# TopicLLM — Python reference implementation

Working implementation of the five-stage pipeline described in *Coherence-Optimized
Topic Modeling with Democratic Large Language Model Interpretation* (Thomas, Murthy,
Pinedo, Loukas & Pasch, 2026).
The archival dissertation code (Supplementary Files S1–S3) is preserved as published;
this package is the maintained version, written against the current OpenAI SDK, that
actually runs the analysis end to end.

## The five stages

| Stage | Script | What it does | API cost |
|---|---|---|---|
| 1 | `stage1_topic_discovery.py` | BERTopic under randomized hyperparameter search; selects the model maximizing c_v coherence; full audit trail | none |
| 2 | `stage2_democratic_naming.py` | Names each topic by plurality vote over thousands of independent LLM queries; writes ballots + tallies | yes |
| 3 | `stage3_synthesis_worksheet.py` | Builds the two-researcher review packet; consensus is recorded by humans in `theme_map.csv` | none |
| 4 | `stage4_classification.py` | Pilots Boolean-dictionary and LLM classifiers against a human benchmark; refuses to scale below the agreement threshold; classifies the full corpus | yes |
| 5 | `stage5_inference.py` | Theme prevalence — whole-corpus counts and shares, prevalence by period, and proportional z-tests with Bonferroni correction | none |

## Start from the repository root

The primary installation, agent workflow, synthetic acceptance profiles and research-review commands are in [REPRODUCE.md](../REPRODUCE.md). Read [AGENTS.md](../AGENTS.md) with your agent before substantive work.

```sh
python -m pip install ".[dev]"
topicllm --profile quickcheck --output-dir runs/quickcheck
python -m pytest dtm_pipeline/tests -q
```

The quickcheck uses generator truth and exercises inference only; it does not call an LLM. Install `".[ml,dev]"` for BERTopic discovery. The downloadable wheel includes the same synthetic data as the repository.

`--profile synthetic-e2e --votes 20 --budget-usd 5` runs all stages with real model calls and an explicitly synthetic review fixture. Its mapping is not human review. The `mock` backend is a separate teaching test and can correctly fail the validation gate; do not weaken thresholds to force completion.

## Your own corpus

Stage 4 requires `stage3/review_record.json` bound to the current evidence, not only a theme map. Record the actual two researchers after review using the command in [REPRODUCE.md](../REPRODUCE.md). Never use the bundled synthetic benchmark to validate other research data.


```sh
topicllm --config research.json --stages 1
topicllm --config research.json --stages 2,3 --votes 20 --budget-usd 5
# Complete the review packet and record actual decisions using REPRODUCE.md.
topicllm --config research.json --stages 4,5 --budget-usd 5
```

Input format: a CSV with a `tweet` column (verbatim document text) and, for the
Stage 5 period comparisons, a `date` column (`YYYY-MM-DD`; set `periods` in
`config.py`). The benchmark needs `tweet` and `human_label` columns, with labels
drawn from the theme names plus the residual option. `custom_stopwords.txt` is
the domain list released with the reference implementation (brand terms and
temporal references).

Other overrides: `--iterations`, `--seed`, `--votes`, `--workers` (concurrent
Stage 4 calls). `--score-archival` scores any existing `*_label` columns in a
benchmark file against `human_label` without API calls.

## Tests

```bash
python -m pytest dtm_pipeline/tests -q     # from the repository root; no API calls
```

The tests cover:

- the Stage 4 safeguards: failed calls are never counted as a theme, interrupted runs resume, and blank corpus documents are rejected;
- canonicalization of model responses;
- the Boolean pilot;
- that the shipped demonstration files match the generator;
- that ground-truth inference matches the published rounded prevalence table by construction;
- evidence-bound researcher review and synthetic-only fixture restrictions;
- persistent budgets, cached responses and the installed OpenAI SDK contract with offline HTTP fixtures.

## Restricted study data

Original study posts are not distributed because of privacy and IRB obligations. The public tool uses fully synthetic records only. No original records, fitted study model or historical ballots are available for this demonstration.

## Configuration

Defaults live in `config.py`; supply an analysis-specific JSON configuration with `--config` and record the effective settings. Defaults follow the documented search and voting budgets, with the maintained deviations described in the revised methods: 50 search iterations × 24 topic solutions = 1,200
candidate models; 5,000 votes per topic at temperature 0.5 / max_tokens 15;
classification at temperature 0.5 / max_tokens 120 (archival value: 30); 85% benchmark-agreement gate.
`domain_context` is one domain-specific input in the prompts — change it
(and the Stage 3 literature lens) to redeploy the pipeline in a new domain.

## Cost control

Paid calls require an explicit `--budget-usd` and persistent reservations; the ledger includes previous attempts in the same output directory. Review the dated price schedule before changing the model.

Stage 2's planned count before retries is `topics × votes_per_topic` API calls. Set
`early_stop = True` in `config.py` to halt a topic's vote once the modal label
holds ≥ `early_stop_share` of ballots after `early_stop_window` votes . This is a cumulative-share heuristic, not a statistical convergence test. Report whatever settings
you use; the ballots and tallies are written to disk either way so the vote is
publishable.

## Reproducibility artifacts

Every stage emits the evidence the paper says to publish alongside findings.
Stage 1 seeds both the hyperparameter draws and every UMAP fit, to control randomness within a fixed environment. A seed alone does not guarantee cross-environment identity. Stage 4 checkpoints corpus classification and
resumes after an interruption, and it never folds failed API calls into a
theme. The artifacts are:
`all_iteration_results.json` (hyperparameter log, seeded), `vote_log.csv` /
`vote_tallies.csv` (the raw and counted ballots), `benchmark_report.json`
(classifier agreement), and `theme_counts.csv` / `ztest_results.csv` (the
prevalence estimates and tests). Pin and report `llm_model`;
label distributions may shift across model versions.

## Relationship to the dissertation code

S1–S3 (plain-text supplements to the paper) are the archival implementations
from the source dissertation, with S2/S3 written against `openai==0.27.0`.
This package documents its changes to archival logic and parameters while modernizing the SDK
surface, seeding the random search, and adding the benchmark gate, vote
tallying, the Stage 3 worksheet hand-off, and the Stage 5 prevalence
statistics as runnable code.

## Recorded environment and saved models

The full synthetic validation used Windows, Python 3.12 and the exact versions in `requirements-lock-windows-py312.txt`. Install that lock in a clean environment to repeat the tested software setup. Other operating systems may require a separately validated lock. The normal `requirements.txt` remains the broad dependency specification.

The default MiniLM revision is pinned to `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. When choosing another embedding model, set its own `embedding_revision` (or explicitly use `None` and record the resolved revision). Stage 1 records effective stopwords, input hash, dependency versions and all attempted candidates, including failures. Its `best_model/fitted_model.pkl` contains the fitted candidate that earned the winning score, including UMAP and HDBSCAN, and the manifest records its hash. Pickles can execute code: load only a model you created and trust, in the recorded environment.

Stage 2 keeps an append-only `all_naming_attempts.jsonl`. Completed topics resume without new votes; an incomplete topic is restarted, with its earlier attempt preserved. Browser research-record downloads preserve available partial response metadata for inspection; loading a record restores inputs and requires rerunning stages.
