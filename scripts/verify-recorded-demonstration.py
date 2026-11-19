"""Verify the recorded Trump demonstration against source, cache and budget.

Requires the author's private run artifacts and research configuration. This is
application-specific verification, not an acceptance test for other corpora.
It publishes only the aggregate verification record; makes no API calls.
"""
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
import argparse,csv,json,hashlib,sqlite3,sys
if not __debug__:
    raise RuntimeError('Run verification without Python optimization; assertions must remain active.')
repo=Path(__file__).resolve().parents[1];sys.path.insert(0,str(repo))
from dtm_pipeline.config import PipelineConfig
from dtm_pipeline.sampling import read_selected
from dtm_pipeline.stage4_classification import canonicalize,build_prompt,SYSTEM
from dtm_pipeline.api_budget import request_fingerprint
from dtm_pipeline.demonstration import require_demonstration_exception
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
rows=lambda p:list(csv.DictReader(p.open(encoding='utf-8',newline='')))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config',required=True)
args=parser.parse_args();cfg=PipelineConfig(**read(Path(args.config)));run=Path(cfg.output_dir)
require_demonstration_exception(cfg)
source,selection=read_selected(cfg,'target');classified=rows(run/'stage4/classified_corpus.csv')
assert len(source)==len(classified)==26239
assert len({x['post_id'] for x in classified})==26239
for expected,observed in zip(source,classified):
    assert all(observed[k]==str(v) for k,v in expected.items()),expected['post_id']
    assert observed['status']=='matched'
    assert observed['classifier']=='llm:gpt-4o-2024-08-06'
    assert canonicalize(observed['raw_response'],cfg)==(observed['theme'],'matched')
assert sha(run/'stage3/codebook.json')=='552617f68c1a7213522df33c5dcf03077400cc698b3788a20d6e5242b8c9f961'
assert sha(run/'stage4/classifier_selection.json')=='86924834442be005cd103a2492c1e5fe6906f20a6e73852b430c86552bb89438'
assert not read(run/'stage4/validation_report.json')['gate_passed']
assert not (run/'stage4/validation_review.json').exists()
assert not read(run/'stage4/classification_status.json')['classifier_validated']
start=read(run/'stage4/demonstration_execution_start.json')
assert all(sha(repo/name)==h for name,h in start['execution_source_sha256'].items())
db=sqlite3.connect((run/'api_ledger.sqlite').as_uri()+'?mode=ro',uri=True)
cache={k:(h,json.loads(r)) for k,h,r in db.execute("SELECT logical_key,fingerprint,result FROM responses WHERE logical_key LIKE 'corpus:%'")}
for i,observed in enumerate(classified):
    expected_hash=request_fingerprint(cfg.llm_model,SYSTEM,build_prompt(observed['tweet'],cfg),cfg.classify_max_tokens,cfg.classify_temperature)
    for attempt in range(max(1,cfg.max_retries)):
        key=f'corpus:{i}' if attempt==0 else f'corpus:{i}:format-retry:{attempt}'
        if key not in cache:continue
        h,response=cache[key];assert h==expected_hash
        parsed,status=canonicalize(response['text'],cfg)
        if status=='matched':
            assert response['text'].strip()==observed['raw_response'] and parsed==observed['theme'];break
    else:raise ValueError('No matching retained provider response for '+str(i))
counts=Counter(x['theme'] for x in classified);table=rows(run/'stage5/theme_counts.csv')
assert {x['theme'] for x in table}==set(cfg.themes+[cfg.none_label])
assert len(table)==13 and sum(int(x['documents']) for x in table)==26239
for x in table:
    assert int(x['documents'])==counts[x['theme']] and int(x['denominator'])==26239
    assert abs(float(x['share'])-counts[x['theme']]/26239)<1e-12
estimand=read(run/'stage5/estimand.json')
assert estimand['model_mode']=='unvalidated-demonstration' and estimand['classifier_validated'] is False
assert estimand['classified_corpus_sha256']==sha(run/'stage4/classified_corpus.csv')
calls=db.execute("SELECT status,charged,result FROM calls WHERE logical_key LIKE 'corpus:%'").fetchall()
assert all(x[0]!='reserved' for x in calls)
usage=[json.loads(x[2] or '{}').get('usage',{}) for x in calls]
total=db.execute('SELECT SUM(charged)/1e9 FROM calls').fetchone()[0]
assert total<=150
out={'verified_at':datetime.now(timezone.utc).isoformat(),'status':'pass','interpretation':estimand['interpretation'],
    'verifier_script':'scripts/verify-recorded-demonstration.py','verifier_script_sha256':sha(Path(__file__)),
    'classifier_validated':False,'heldout_gate_passed':False,'target_posts':26239,'unique_target_ids':26239,
    'source_fields_verified':True,'valid_assignments':26239,'missing_or_unresolved':0,
    'raw_responses_reparsed':26239,'cached_request_fingerprints_verified':26239,'codebook_and_classifier_unchanged':True,
    'execution_source_unchanged_during_run':True,'source_selection':selection,
    'corpus_attempts':len(calls),'corpus_successful_calls':sum(x[0]=='success' for x in calls),
    'corpus_failed_attempts':sum(x[0]=='failed' for x in calls),'corpus_accounted_usd':sum(x[1] for x in calls)/1e9,
    'prompt_tokens':sum(x.get('prompt_tokens',0) for x in usage),'completion_tokens':sum(x.get('completion_tokens',0) for x in usage),
    'cumulative_research_accounted_usd':total,'authorized_cumulative_ceiling_usd':150,
    'rows':[{'theme':x['theme'],'documents':int(x['documents']),'denominator':26239,'share':float(x['share'])} for x in table],
    'classified_corpus_sha256':sha(run/'stage4/classified_corpus.csv'),'counts_sha256':sha(run/'stage5/theme_counts.csv'),
    'counts_hash_scope':'Raw stage5/theme_counts.csv before publication adds classifier_validated and interpretation columns. The published CSV checksum is in artifact-integrity.json; its count, denominator and share values must match the rows recorded here.',
    'private_annotation_policy':'Aggregate results only; human labels, adjudication notes and post-level predictions retained privately.'}
(run/'stage5/demonstration_verification.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps(out,indent=2,ensure_ascii=False))
