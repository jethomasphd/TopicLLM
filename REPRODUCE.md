# Run TopicLLM

Every command, from the free install check to the final report. Part A reruns the Trump tutorial; Part B uses your own text. The four human decisions are marked **🟧 You decide**. An agent prepares the evidence for those steps and then stops; it never supplies them.

## 0. Install and check

Python 3.11 or newer, in a fresh environment.

```bash
git clone https://github.com/jethomasphd/TopicLLM && cd TopicLLM
python -m venv .venv
source .venv/bin/activate            # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install ".[dev]"
topicllm --profile quickcheck --output-dir runs/quickcheck
```

The quickcheck verifies the bundled archive's hashes, IDs, dates and counts. It is free and offline, and it checks the installation, not the science. Record `git rev-parse HEAD` and `python -m pip freeze` with your run.

Topic discovery needs the ML extra: `python -m pip install ".[ml]"`. It runs locally and makes no paid calls. A Windows/Python 3.12 lock file is in `dtm_pipeline/requirements-lock-windows-py312.txt`.

## Part A · The Trump tutorial

One archive, two windows, both inclusive: topics are discovered in the campaign (**2015-06-16 to 2016-11-08**, 7,805 posts) and measured in the first term (**2017-01-20 to 2021-01-08**, 26,239 posts). The 372 posts between them belong to neither window.

```bash
cp examples/campaign-presidency-config.json research-config.json   # set output_dir to a new folder
topicllm --profile research --config research-config.json --stages all --plan
```

`--plan` prints record counts, planned calls and a rough cost for each paid stage, and runs nothing.

### 1. Discover

```bash
topicllm --profile research --config research-config.json --stages 1
```

The search makes 50 base fits and reduces each to every topic ceiling from 2 to 25 (1,200 candidates), keeping every score, size and assignment. **The selection rule:** a candidate is eligible only if no topic holds more than half of the assigned documents (`max_topic_share`, default 0.5) and it has at least `min_topics` topics (default 2). Among eligible candidates, the highest c<sub>v</sub> coherence wins. The unconstrained winner is still recorded, and `stage1/selection_sensitivity.json` shows which candidate wins across thresholds. Declare stricter values in the config before you run, not after.

**🟧 You decide:** read the selected topics' original posts and outliers. To adopt a different saved candidate, run `python scripts/select-campaign-candidate.py --help` (installed command: `topicllm-select-candidate`). It records your rationale and keeps the automatic choice. Never tune discovery against first-term results.

### 2. Name

```bash
export OPENAI_API_KEY=...   # in your shell, never in a config file, a chat or Git
topicllm --profile research --config research-config.json --stages 2,3 --plan
topicllm --profile research --config research-config.json --stages 2,3 --budget-usd YOUR_TOTAL
```

The tutorial uses 500 calls per topic at temperature 0.5. Raw ballots and tallies are kept. The budget covers every attempt in the run folder, including retries and resumed runs; when it runs out, work stops and nothing is invented to fill the gap.

### 3. Define

**🟧 You decide (two researchers):** open `stage3/synthesis_workspace.html`. Read the original posts, the outliers, the words and the ballots. Combine topics that share a meaning, keep distinct ones apart, and write the codebook: each theme's definition, what to include and exclude, examples, and a rule for picking one primary theme. Export the decision record, then:

```bash
python scripts/import-synthesis.py --config research-config.json --review TopicLLM-human-synthesis.json --output-config research-approved.json
topicllm --profile research --config research-approved.json --record-review --reviewers "First researcher" "Second researcher"
```

The record binds your approval to hashes of the source, windows, assignments, ballots, map and codebook; changing any of them voids it. The residual label is exactly `The text does not fit into any of these themes`. Use `research-approved.json` from here on.

### 4. Check

Agree the sample sizes first (the tutorial used 100 development and 250 held-out posts). The held-out sample is drawn first, by simple random sampling from the target; the development sample excludes its IDs and exact texts.

```bash
python scripts/prepare-annotations.py --config research-approved.json --output runs/annotations --development-n 100 --evaluation-n 250
```

**🟧 You decide (two coders):** each coder labels both samples alone, in the generated local pages, without seeing the other's labels or any model output. Merge, then adjudicate every disagreement together:

```bash
python scripts/prepare-annotations.py --config research-approved.json --output runs/annotations/development_labels.csv --reviewer-exports coder-one-development.csv coder-two-development.csv
python scripts/prepare-adjudication.py --config research-approved.json --source runs/annotations/development_labels.csv --phase development --output development-adjudication.html
python scripts/prepare-adjudication.py --config research-approved.json --source runs/annotations/development_labels.csv --phase development --check development-adjudicated.csv
topicllm --profile research --config research-approved.json --record-annotations development-adjudicated.csv --reviewers "First coder" "Second coder"
```

Set `development_csv`, `benchmark_csv` and `annotation_manifest` in the config. Then choose the classifier on development data, freeze it, and only then test it on the held-out sample:

```bash
topicllm --profile research --config research-approved.json --stages 4 --stage4-action development --budget-usd YOUR_TOTAL
# only after the choice is frozen and the held-out labels are adjudicated:
topicllm --profile research --config research-approved.json --stages 4 --stage4-action validate --budget-usd YOUR_TOTAL
```

The gate requires agreement strictly above 0.85 and, for every theme, positive support and nonzero recall. **🟧 You decide (both researchers):** read the per-theme precision and recall, the confusion counts and the individual errors. Passing is necessary, not sufficient. If it fails, revise on development evidence, freeze again and test on a **fresh** held-out sample; an opened test set is no longer independent.

### 5. Report

```bash
topicllm --profile research --config research-approved.json --record-validation-review --reviewers "First researcher" "Second researcher"
topicllm --profile research --config research-approved.json --stages 4 --stage4-action classify --budget-usd YOUR_TOTAL
topicllm --profile research --config research-approved.json --stages 5
```

`stage5/theme_counts.csv` gives every theme's count, the common denominator and its share, including zero-count themes and the residual. Every target ID must appear exactly once, and failed responses block the report rather than becoming "fits no theme." The residual mixes off-codebook content with classifier misses, so it cannot by itself show that a theme is absent.

**In the recorded tutorial,** the check failed at 70% agreement. The author recorded a demonstration-only exception ([`demonstration_exception.json`](docs/data/trump/campaign/demonstration_exception.json)) so that stage 5 could be shown; its shares stay labeled as unvalidated model-assigned shares. The tutorial's finding comes from the human-coded random sample instead: `python scripts/estimate-human-sample-prevalence.py`. Never create such an exception without the investigator's explicit decision.

## Part B · Your own text

One CSV, one row per document. Required: a text column. Recommended: a unique ID column. Optional: a `date` column (`YYYY-MM-DD`), needed only for discovery and target windows.

```bash
cp examples/your-data-config.json my-config.json
# edit: input_csv, text_column, id_column, domain_context, output_dir
topicllm --profile research --config my-config.json --stages all --plan
```

Then follow steps 1–5 above with `my-config.json`. Notes:

- **Stopwords:** `"stopwords_file": null` uses NLTK's English list. The bundled default adds Twitter tokens (`rt`, `https`, `amp`, `realdonaldtrump`) and warns you if you use it on other data.
- **Windows:** without dates, discovery and measurement use the same documents. That's fine for describing one collection, but the tutorial's campaign-to-term separation is stronger when you have it.
- **Naming budget:** 100–200 votes per topic usually show the same leading names as 500.
- **Cost:** the full-corpus classification dominates. In the tutorial, 26,263 calls of about 1,600 prompt tokens cost $107 with GPT-4o. `--plan` estimates yours from your codebook and document lengths.
- `examples/sample-reviews.csv` has 40 synthetic rows to show the format; it is too small for real discovery.

## Evidence to keep

Keep the commit, dependencies, config, seeds, embedding revision, stopwords, every candidate and the selection record, ballots, the human synthesis and codebook, both coders' labels and the adjudication, the frozen classifier, the evaluation and acceptance records, classifications, counts and `api_ledger.sqlite`. Load fitted-model pickles only in the environment that made them. Seeds support repetition in one environment; they don't guarantee identical clusters or LLM answers across hardware, libraries or model revisions.

## Maintainer checks

```bash
python -m pytest dtm_pipeline/tests -q
node --test tests/*.test.mjs
node scripts/verify-sources.mjs
python scripts/check-published-metrics.py
python scripts/check-publication-privacy.py
```

Building and publishing the site, figures, paper and package is covered in [MAINTAINING.md](MAINTAINING.md).
