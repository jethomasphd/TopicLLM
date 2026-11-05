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

## Quickstart

Out of the box the pipeline runs on the open demonstration corpus in
[`../docs/data/`](../docs/data/): 5,872 fully synthetic posts from 11 fictional
brands, a 250-post human-labeled benchmark, and ground-truth themes. It is
calibrated to the published demonstration (see the [data card](../docs/data/README.md)).

```bash
pip install -r requirements.txt

python run_pipeline.py --stages 1                  # coherence-optimized discovery (no API cost)
python run_pipeline.py --stages 2,3 --mock-llm     # democratic naming + review packet, keyless dry run
python run_pipeline.py --ground-truth --stages 5   # reference inference from the ground truth
```

`--mock-llm` swaps in a deterministic, keyless stand-in for Stages 2 and 4, so
every stage can be exercised at no cost. Its outputs are labeled `MOCK` and are
not measurements. With `OPENAI_API_KEY` set and no `--mock-llm`, Stages 2 and 4
call the model named in `config.py`.

`--ground-truth` feeds Stage 5 the corpus's true themes in place of a Stage 4
classification. Because the corpus is calibrated to the published demonstration,
this returns the published prevalence table and z statistics, which checks the
inference code. A real classifier's results approach that table as its agreement
with the ground truth rises.

`make_demo_data.py` rebuilds the demonstration corpus byte for byte (seeded).

## Your own corpus

```bash
python run_pipeline.py --input your_corpus.csv --stopwords your_stopwords.txt \
    --benchmark your_labels.csv --output-dir my_run --stages 1,2,3
#   -> after the two-researcher consensus, complete my_run/stage3/theme_map_TEMPLATE.csv,
#      save it as theme_map.csv, and set `themes` in config.py to the agreed names
python run_pipeline.py --input your_corpus.csv --benchmark your_labels.csv \
    --output-dir my_run --stages 4,5
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
python -m pytest tests -q     # a few seconds; no API calls
```

The tests check five things:

- the Stage 4 safeguards: failed calls are never counted as a theme, interrupted runs resume, and blank documents are labeled without a call;
- canonicalization of model responses;
- the Boolean pilot;
- that the shipped demonstration files match the generator;
- that ground-truth inference reproduces the published table.

## Data availability

The dissertation data are restricted. They are brand tweets recorded by the
Prevention Research Lab Twitter Marketing Study, and user-generated tweets from
the Computational Media Lab COVID-19 Twitter Dataset. The data contain
account-level information and content governed by the platform's terms of service
and by the agreements under which they were collected, so they are not posted
publicly. They are available from the corresponding author
(jethomasphd@gmail.com) on reasonable request for non-commercial research, under
a data use agreement consistent with those terms.

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

Every stage emits the evidence the paper says to publish alongside findings.
Stage 1 seeds both the hyperparameter draws and every UMAP fit, so a run is
reproducible from `config.py`. Stage 4 checkpoints corpus classification and
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
This package preserves their logic and parameters while modernizing the SDK
surface, seeding the random search, and adding the benchmark gate, vote
tallying, the Stage 3 worksheet hand-off, and the Stage 5 prevalence
statistics as runnable code.
