"""Persistent, conservative API reservations and an auditable response cache.

Amounts are integer nano-USD. Uncertain requests retain their reservation.
The price schedule is GPT-4o standard pricing verified 2026-11-16:
https://developers.openai.com/api/docs/models/gpt-4o ($2.50/$10 per 1M tokens).
"""
import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path


class BudgetExceeded(RuntimeError):
    pass


class ApiBudget:
    def __init__(self, cfg):
        if cfg.llm_model != 'gpt-4o-2024-08-06':
            raise ValueError('Update and verify the budget price schedule before using another model.')
        if cfg.api_budget_usd is None or not 0 < cfg.api_budget_usd <= 1000:
            raise ValueError('Set an explicit positive --budget-usd before paid calls.')
        self.cfg = cfg
        self.root = Path(cfg.output_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / 'api_ledger.sqlite'
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS calls (id TEXT PRIMARY KEY, logical_key TEXT, fingerprint TEXT, at TEXT, reserved INTEGER, charged INTEGER, status TEXT, result TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS responses (logical_key TEXT PRIMARY KEY, fingerprint TEXT, result TEXT)')

    def connect(self):
        return sqlite3.connect(self.path, timeout=60)

    def cached(self, key, digest):
        with self.connect() as db:
            row = db.execute('SELECT fingerprint,result FROM responses WHERE logical_key=?', (key,)).fetchone()
        if row and row[0] != digest:
            raise ValueError('Cached API operation has changed inputs/settings; use a new output directory.')
        return json.loads(row[1]) if row else None

    def reserve(self, key, digest, system, user, max_tokens):
        # A UTF-8 byte bound plus message framing conservatively bounds input tokens.
        upper = (len(system.encode()) + len(user.encode()) + 256) * 2500 + max_tokens * 10000
        call_id = str(uuid.uuid4())
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            spent, count = db.execute('SELECT COALESCE(SUM(charged),0),COUNT(*) FROM calls').fetchone()
            if spent + upper > round(self.cfg.api_budget_usd * 1_000_000_000) or count >= self.cfg.max_api_calls:
                raise BudgetExceeded('API budget or call ceiling reached. Completed responses are cached; raise the authorized ceiling to resume.')
            db.execute('INSERT INTO calls VALUES (?,?,?,?,?,?,?,?)', (call_id,key,digest,datetime.now(timezone.utc).isoformat(),upper,upper,'reserved',None))
        return call_id

    def settle(self, call_id, key, digest, result=None, error=None):
        with self.connect() as db:
            reserved = db.execute('SELECT reserved FROM calls WHERE id=?',(call_id,)).fetchone()[0]
            usage = (result or {}).get('usage') or {}
            # Ignore caching discounts: conservatively charge the ordinary input rate.
            known = isinstance(usage.get('prompt_tokens'), int) and isinstance(usage.get('completion_tokens'), int)
            actual = usage['prompt_tokens']*2500 + usage['completion_tokens']*10000 if known else reserved
            if actual > reserved:
                error = 'Provider usage exceeded the reservation; review the price/token bound.'
            value = json.dumps(result if result else {'error_type':error}, ensure_ascii=False)
            db.execute('UPDATE calls SET charged=?,status=?,result=? WHERE id=?', (actual,'success' if result and not error else 'failed',value,call_id))
            if result and not error:
                db.execute('INSERT OR REPLACE INTO responses VALUES (?,?,?)',(key,digest,value))
        # The caller exports a consistent report at stage boundaries; the SQLite
        # transaction above is the durable audit record for every request.
        if result and error:
            raise BudgetExceeded(error)

    def export(self):
        with self.connect() as db:
            rows = db.execute('SELECT id,logical_key,fingerprint,at,reserved,charged,status,result FROM calls ORDER BY at,id').fetchall()
        records = [dict(zip(['id','operation','input_sha256','at','reserved_nano_usd','charged_nano_usd','status','response'],row)) for row in rows]
        for row in records:
            row['response'] = json.loads(row['response']) if row['response'] else None
        summary = {'price_date':'2026-11-16','model':self.cfg.llm_model,'input_usd_per_million':2.5,'output_usd_per_million':10,
                   'budget_usd':self.cfg.api_budget_usd,'call_ceiling':self.cfg.max_api_calls,'attempted_calls':len(records),
                   'successful_calls':sum(r['status']=='success' for r in records),'conservatively_accounted_usd':sum(r['charged_nano_usd'] for r in records)/1e9,
                   'prompt_tokens':sum((r['response'] or {}).get('usage',{}).get('prompt_tokens',0) for r in records),
                   'completion_tokens':sum((r['response'] or {}).get('usage',{}).get('completion_tokens',0) for r in records)}
        # Export from the database on demand; concurrent writers never modify the ledger file directly.
        for name, value in [('api_usage.json',summary),('api_responses.json',records)]:
            temporary = self.root / (name + '.' + uuid.uuid4().hex + '.tmp')
            temporary.write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf-8')
            temporary.replace(self.root/name)
        return summary


def request_fingerprint(model, system, user, max_tokens, temperature):
    return hashlib.sha256(json.dumps([model,system,user,max_tokens,temperature],ensure_ascii=False).encode()).hexdigest()
