# The `topicllm` Python package

This is the code behind TopicLLM's five stages. Install it from the repository root with `python -m pip install ".[dev]"`, adding `".[ml]"` for topic discovery. Commands are in [REPRODUCE.md](../REPRODUCE.md); agent rules are in [AGENTS.md](../AGENTS.md).

| Module | Stage | What it does |
|---|---|---|
| `sampling.py` | — | Reads the CSV (configurable `text_column`/`id_column`), applies date windows, rejects duplicate IDs and invalid dates, hashes the selection |
| `stage1_topic_discovery.py`, `selection_rule.py` | Discover | Randomized BERTopic search over 1,200 candidates; selects the highest c<sub>v</sub> coherence among candidates where no topic holds more than `max_topic_share` of documents and there are at least `min_topics`; records the unconstrained winner and a sensitivity table |
| `selection.py` | Discover | `topicllm-select-candidate`: a researcher adopts a different saved candidate, with a recorded rationale |
| `stage2_democratic_naming.py` | Name | Repeated LLM naming with a declared vote budget; raw ballots and tallies |
| `stage3_synthesis_worksheet.py`, `synthesis_review.py`, `review.py` | Define | Local review workspace, import of the two researchers' decisions, evidence-bound approval |
| `annotations.py`, `adjudication.py` | Check | Held-out and development samples, local coding pages without model output, merge and adjudication |
| `research_validation.py`, `stage4_classification.py` | Check | Classifier development, frozen held-out validation, acceptance gate, corpus classification |
| `stage5_inference.py` | Report | Counts, common denominator and shares for every theme and the residual |
| `api_budget.py`, `llm_backend.py` | — | Persistent spending ledger, retries and resumable caching; OpenAI, gateway and labeled mock backends |
| `demonstration.py` | — | Verifies the recorded tutorial's demonstration-only exception; it never marks a classifier validated |

Profiles: `quickcheck` verifies the bundled archive offline. `trump-demo` runs tutorial discovery on the bundled corpus. `research` runs any JSON configuration. `--plan` prints counts, calls and a rough cost without running anything, and paid stages require `--budget-usd`. Mock backends are engineering fixtures and can't supply research findings.
