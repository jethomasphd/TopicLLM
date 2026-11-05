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

ERROR_LABEL = "__API_ERROR__"  # never silently folded into a theme


class LLMBackend:
    name = "base"

    def __init__(self, cfg):
        self.cfg = cfg

    @property
    def model_id(self) -> str:
        return self.cfg.llm_model

    def complete(self, system: str, user: str, max_tokens: int,
                 temperature: float, tag: str = "llm") -> str:
        """One independent completion with retry/backoff; returns
        ERROR_LABEL if every attempt fails."""
        for attempt in range(self.cfg.max_retries):
            try:
                return self._complete(system, user, max_tokens, temperature).strip()
            except Exception as e:  # noqa: BLE001 — any API failure is retried
                wait = 2 ** (attempt + 1)
                print(f"[{tag}]   API error ({e}); retry {attempt + 1}/"
                      f"{self.cfg.max_retries} in {wait}s")
                time.sleep(wait)
        return ERROR_LABEL

    def _complete(self, system, user, max_tokens, temperature) -> str:
        raise NotImplementedError


class OpenAIBackend(LLMBackend):
    name = "openai"

    def __init__(self, cfg):
        super().__init__(cfg)
        from openai import OpenAI  # pip install openai>=1.0
        self.client = OpenAI()     # reads OPENAI_API_KEY from the environment

    def _complete(self, system, user, max_tokens, temperature) -> str:
        resp = self.client.chat.completions.create(
            model=self.cfg.llm_model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            max_tokens=max_tokens,
            temperature=temperature,
            n=1,
        )
        return resp.choices[0].message.content or ""


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
    if backend == "mock":
        print("[llm] *** MOCK backend: outputs exercise the pipeline but are NOT "
              "LLM measurements. Do not report them. ***")
        return MockBackend(cfg)
    raise ValueError(f"Unknown llm_backend '{backend}' (expected 'openai' or 'mock').")
