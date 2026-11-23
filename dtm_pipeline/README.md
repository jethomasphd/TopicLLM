# The `topicllm` Python package

This package runs TopicLLM's five stages: discover topics, propose names, define themes through human review, check classifications, and report theme shares. If you are new to the workflow, start with the [browser tutorial](https://topicllm.dev/tutorial/) or the [current software paper](https://topicllm.dev/paper/).

For a project you will adapt with a coding agent, fork or clone the repository and install from its root with `python -m pip install ".[dev]"`, adding `".[ml]"` for topic discovery. Commands are in [REPRODUCE.md](../REPRODUCE.md); agent rules are in [AGENTS.md](../AGENTS.md).

For the package alone, download the wheel from the [release page](https://github.com/jethomasphd/TopicLLM/releases) and run these commands in the download directory:

```sh
python -m pip install ./topicllm_research-0.7.0-py3-none-any.whl
topicllm --profile quickcheck --output-dir runs/quickcheck
```

The offline check verifies the bundled archive without model calls. It is the first installation check, not a completed research analysis. The package is distributed through GitHub releases; it is not published on PyPI.

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
