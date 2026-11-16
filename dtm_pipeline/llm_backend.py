"""
llm_backend.py — The one place Stages 2 and 4 talk to a language model.

Backends
  openai : the reference backend (current OpenAI SDK, openai>=1.0). Decoding
           parameters are passed through unchanged from config.py.
  mock   : a deterministic, keyless stand-in for dry runs on real data. It
           exercises every code path (vote tallying, canonicalization, the
           benchmark gate, checkpointing, Stage 5) without API cost. Its
           outputs are NOT measurements: every artifact produced with it is
           labeled model="MOCK".

Both backends share the retry/backoff policy of the reference implementation
(max_retries attempts, exponential backoff 2, 4, 8, ... seconds).
"""

from __future__ import annotations

import hashlib
import re
import time
import os
import json
import uuid
from urllib.request import Request, urlopen
from urllib.error import HTTPError
if __package__:
    from .api_budget import ApiBudget, BudgetExceeded, request_fingerprint
else:
    from api_budget import ApiBudget, BudgetExceeded, request_fingerprint

ERROR_LABEL = "__API_ERROR__"  # never silently folded into a theme


class LLMBackend:
    name = "base"

    def __init__(self, cfg):
        self.cfg = cfg
        self.budget = ApiBudget(cfg) if self.name in ('openai','gateway') else None

    @property
    def model_id(self) -> str:
        return self.cfg.llm_model

    def complete(self, system: str, user: str, max_tokens: int,
                 temperature: float, tag: str = "llm", request_key=None, task_data=None) -> str:
        """One independent completion with retry/backoff; returns
        ERROR_LABEL if every attempt fails."""
        key = request_key or str(uuid.uuid4())
        digest = request_fingerprint(self.model_id,system,user,max_tokens,temperature)
        cached = self.budget.cached(key,digest) if self.budget else None
        if cached:
            return cached['text']
        for attempt in range(self.cfg.max_retries):
            call_id = self.budget.reserve(key,digest,system,user,max_tokens) if self.budget else None
            try:
                operation=hashlib.sha256(f'{key}:{digest}:{attempt}'.encode()).hexdigest()
                result = self._gateway(task_data,operation) if self.name == 'gateway' else self._complete(system, user, max_tokens, temperature)
                if isinstance(result,str): result = {'text':result,'model':self.model_id}
                if not result.get('text','').strip(): raise ValueError('Empty model response')
                if self.budget: self.budget.settle(call_id,key,digest,result=result)
                return result['text'].strip()
            except BudgetExceeded:
                raise
            except Exception as e:
                if self.budget: self.budget.settle(call_id,key,digest,error=type(e).__name__)
                status = getattr(e,'status_code',None)
                body = getattr(e,'body',{}) or {}
                code = body.get('code') or body.get('error',{}).get('code') if isinstance(body,dict) else None
                if getattr(e,'retryable',True) is False or status in (400,401,403,404) or code in ('insufficient_quota','credit_balance_exhausted','organization_spend_limit_exceeded','project_spend_limit_exceeded','organization_usage_limit_exceeded'):
                    print(f'[{tag}] Non-retryable provider failure ({type(e).__name__}); no label recorded.')
                    return ERROR_LABEL
                if attempt + 1 >= self.cfg.max_retries: break
                wait = max(2 ** (attempt + 1),getattr(e,'retry_after',0))
                print(f"[{tag}] API error ({type(e).__name__}); retry {attempt + 1}/{self.cfg.max_retries} in {wait}s")
                time.sleep(wait)
        return ERROR_LABEL

    def _complete(self, system, user, max_tokens, temperature) -> str:
        raise NotImplementedError


class OpenAIBackend(LLMBackend):
    name = "openai"

    def __init__(self, cfg):
        super().__init__(cfg)
        from openai import OpenAI  # pip install openai>=1.0
        self.client = OpenAI(max_retries=0, timeout=45) # one auditable retry layer

    def _complete(self, system, user, max_tokens, temperature) -> str:
        resp = self.client.chat.completions.create(
            model=self.cfg.llm_model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            max_tokens=max_tokens,
            temperature=temperature,
            n=1,
            store=False,
        )
        if resp.choices[0].finish_reason != "stop":
            raise ValueError("Incomplete model response; no label recorded.")
        return {'text':resp.choices[0].message.content or '', 'model':resp.model,
                'request_id':getattr(resp,'_request_id',None),'system_fingerprint':resp.system_fingerprint,
                'usage':resp.usage.model_dump() if resp.usage else {},'temperature':temperature,'max_tokens':max_tokens}


class GatewayBackend(LLMBackend):
    """Operator-only integration checks; public examples use a separate allowlisted route."""
    name = 'gateway'

    def _gateway(self, task_data, operation):
        if not task_data: raise ValueError('Gateway calls require a structured research task.')
        token = os.environ.get('TOPICLLM_RESEARCH_TOKEN')
        if not token: raise ValueError('TOPICLLM_RESEARCH_TOKEN is not configured.')
        request = Request(self.cfg.gateway_url.rstrip('/')+'/api/llm', data=json.dumps(task_data).encode(),
                          headers={'Content-Type':'application/json','Authorization':'Bearer '+token,'X-Request-ID':operation,
                                   'User-Agent':'TopicLLM/0.3 (+https://github.com/jethomasphd/TopicLLM)'})
        try:
            with urlopen(request,timeout=55) as response:
                result=json.load(response)
                if result.get('model') != self.cfg.llm_model: raise ValueError('Gateway returned a different model than configured.')
                return result
        except HTTPError as error:
            try: body=json.loads(error.read().decode())
            except (ValueError,UnicodeDecodeError): body={}
            error.retryable=body.get('retryable',error.code==429 or error.code>=500)
            error.retry_after=float(error.headers.get('Retry-After','0'))
            raise error


class MockBackend(LLMBackend):
    """Deterministic stand-in. Naming: a title-cased label from the leading
    representative words, with occasional variant ballots so tallying is
    exercised. Classification: picks the option whose words overlap the text
    most, else the residual option."""

    name = "mock"

    @property
    def model_id(self) -> str:
        return "MOCK"

    def __init__(self, cfg):
        super().__init__(cfg)
        self._calls = 0

    def _rand(self, *parts) -> int:
        self._calls += 1
        h = hashlib.sha256("|".join(map(str, parts + (self._calls,))).encode())
        return int(h.hexdigest()[:8], 16)

    def _complete(self, system, user, max_tokens, temperature) -> str:
        if "naming topics" in system:
            m = re.search(r": (.*?)\. Please provide", user, flags=re.S)
            words = [w.strip() for w in (m.group(1) if m else user).split(",") if w.strip()]
            r = self._rand(user)
            k = 3 if r % 10 < 7 else 2  # ~70% / 30% split -> a clear modal label
            return " ".join(w.capitalize() for w in words[:k]) or "Unnamed Topic"
        if "classifying text" in system:
            opts = re.search(r"themes: (.*?)\.Text: ", user, flags=re.S)
            text = re.search(r"Text: (.*)\.Respond with", user, flags=re.S)
            options = [o.strip().rstrip(",").strip()
                       for o in re.split(r"\s*\d+\.\s+", opts.group(1))[1:]] if opts else []
            body = set(re.findall(r"[a-z]+", (text.group(1) if text else "").lower()))
            stop = {"and", "the", "of", "a", "to", "text", "does", "not", "fit",
                    "into", "any", "these", "themes", "media", "social"}
            scores = [len(body & (set(re.findall(r"[a-z]+", o.lower())) - stop))
                      for o in options[:-1]]
            if scores and max(scores) > 0:
                return options[scores.index(max(scores))]
            return options[-1] if options else "The text does not fit into any of these themes"
        return "mock response"


def make_backend(cfg) -> LLMBackend:
    backend = getattr(cfg, "llm_backend", "openai").lower()
    if backend == "openai":
        return OpenAIBackend(cfg)
    if backend == 'gateway':
        return GatewayBackend(cfg)
    if backend == "mock":
        print("[llm] *** MOCK backend: outputs exercise the pipeline but are NOT "
              "LLM measurements. Do not report them. ***")
        return MockBackend(cfg)
    raise ValueError(f"Unknown llm_backend '{backend}' (expected 'openai' or 'mock').")
