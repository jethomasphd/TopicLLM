# Democratic Topic Modeling Pipeline

Working implementation of the five-stage pipeline described in *Coherence-Optimized
Topic Modeling with Democratic Large Language Model Interpretation* (Thomas, 2026).
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
| 5 | `stage5_inference.py` | Proportional z-tests with Bonferroni correction; per-theme corpora for LIWC-22; Stata `.do` file for the cross-lagged GSEM | none |

## Quickstart

```bash
pip install -r requirements.txt
export OPENAI_API_KEY="sk-..."        # needed for stages 2 and 4 only

# Smoke test on synthetic data (no PRL-TMS data required):
python make_demo_data.py              # writes tweet_data.csv + human_labels.csv
python run_pipeline.py --stages 1     # discovery, no API cost

# Full run on your own corpus:
python run_pipeline.py --input your_corpus.csv --stages 1,2,3
#   -> complete pipeline_output/stage3/theme_map_TEMPLATE.csv after the
#      two-researcher consensus, save as theme_map.csv, and set `themes`
#      in config.py to the agreed names
python run_pipeline.py --input your_corpus.csv --stages 4,5
```

Input format: a CSV with a `tweet` column (verbatim document text) and, for the
Stage 5 period comparisons, a `date` column (`YYYY-MM-DD`).

## Configuration

Everything lives in `config.py` — one auditable file. Defaults reproduce the
reference implementation: 50 search iterations × 24 topic solutions = 1,200
candidate models; 5,000 votes per topic at temperature 0.5 / max_tokens 15;
classification at temperature 0.5 / max_tokens 30; 85% benchmark-agreement gate.
`domain_context` is the **only** domain-specific text in the prompts — change it
(and the Stage 3 literature lens) to redeploy the pipeline in a new domain.

## Cost control

Stage 2's upper bound is `topics × votes_per_topic` API calls. Set
`early_stop = True` in `config.py` to halt a topic's vote once the modal label
holds ≥ `early_stop_share` of ballots after `early_stop_window` votes — the
stability-monitoring approach discussed in the paper. Report whatever settings
you use; the ballots and tallies are written to disk either way so the vote is
publishable.

## Reproducibility artifacts

Every stage emits the evidence the paper says to publish alongside findings:
`all_iteration_results.json` (hyperparameter log, seeded), `vote_log.csv` /
`vote_tallies.csv` (the raw and counted ballots), `benchmark_report.json`
(classifier agreement), and `ztest_results.csv`. Pin and report `llm_model`;
label distributions may shift across model versions.

## Relationship to the dissertation code

S1–S3 (plain-text supplements to the paper) are the archival implementations
from the source dissertation, with S2/S3 written against `openai==0.27.0`.
This package preserves their logic and parameters while modernizing the SDK
surface, seeding the random search, and adding the benchmark gate, vote
tallying, and Stage 3/5 hand-offs as runnable code.
