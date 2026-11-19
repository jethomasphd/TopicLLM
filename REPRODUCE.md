# Discover in the campaign. Measure in the presidency.

The worked application uses one public Trump account archive with separate temporal roles: **7,805 campaign posts** for topic discovery and **26,239 presidential posts** for prevalence measurement. The original dissertation and papers remain in the research library; their datasets are not distributed.

The question is: **which themes emerge from campaign posts, and what share of subsequent presidential posts expresses each theme?** The standalone manuscript connects that question to executable scripts, actual human interpretation, and independent evaluation.

## 1. Install and verify

Use Python 3.11+ in a fresh environment. Fork or clone https://github.com/jethomasphd/TopicLLM .

```bash
python -m venv .venv
# PowerShell: .venv/Scripts/Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install ".[dev]"
topicllm --profile quickcheck --output-dir runs/quickcheck
```

Quickcheck verifies the canonical archive's hashes, unique IDs, dates, and counts without model/API calls. Record the commit and `python -m pip freeze`. The Windows/Python 3.12 ML lock records a measured environment, not a universal lock for other platforms.

## 2. Declare the design and discover topics

Copy `examples/campaign-presidency-config.json` to `research-config.json`; set `output_dir` to a new run directory. Discovery is **2015-06-16–2016-11-08**; the target is **2017-01-20–2021-01-08**, both inclusive. The 372 transition records remain in the source but enter neither view. The archive ends January 8, before the constitutional term ended.

With a wheel installation, create the same editable starting point using `topicllm --profile trump-demo --write-config research-config.json`. This exports the effective settings and bundled data paths without executing analysis or making paid calls. Review the JSON before running; the command refuses to overwrite an existing configuration.

The example supplies no approved themes, annotations, or spending authorization. `sampling.py` rejects invalid dates, duplicate IDs and overlapping windows, and records the ordered selected-ID hashes. Retweets and distinct-ID repeated texts remain posting events.

```bash
python -m pip install ".[ml]"
topicllm --profile research --config research-config.json --stages 1 --plan
topicllm --profile research --config research-config.json --stages 1
```

Discovery makes 50 base fits and evaluates ceilings 2–25, using local compute and no paid calls. It retains every candidate's score, sizes, words and assignments, plus the highest-coherence fitted model. Empty modeled text is excluded from discovery only. Inspect topic coverage, outliers and original posts; coherence alone does not establish a useful taxonomy.

If a researcher selects another saved candidate, `scripts/select-campaign-candidate.py` records the rationale, preserves the numerical winner, and requires exact reconstruction of the alternative's assignments and words. Do not silently change the selection rule or tune campaign discovery against presidential outcomes.

An installed wheel supplies the same tools as console commands. Use these equivalents with the same arguments; a fork is not required to use the research gates.

| Checkout command | Installed-package command |
|---|---|
| `python scripts/select-campaign-candidate.py` | `topicllm-select-candidate` |
| `python scripts/prepare-annotations.py` | `topicllm-annotations` |
| `python scripts/import-synthesis.py` | `topicllm-import-synthesis` |

Run any command with `--help` for its arguments. To add discovery dependencies to a wheel installation, use `python -m pip install "./topicllm_research-0.6.4-py3-none-any.whl[ml]"` from the directory containing your downloaded wheel. The `.[ml]` commands in this guide instead refer to a repository checkout.

## 3. Collect naming evidence

The application configuration uses 500 fixed naming calls per adopted topic, temperature 0.5 and a 32-token output maximum. Twelve bounded workers reduce elapsed time. Raw ballots and tallying rules are retained; repeated model answers are not independent human judgments.

Set `OPENAI_API_KEY` privately, or use an explicitly authorized operator gateway. Never put credentials in an agent conversation, configuration file or Git. Inspect both dollar and attempted-call ceilings.

```bash
topicllm --profile research --config research-config.json --stages 2,3 --plan
topicllm --profile research --config research-config.json --stages 2,3 --budget-usd YOUR_APPROVED_TOTAL
```

The total includes all attempts and resumed operations in the run directory. The SQLite ledger retains responses and conservative reservations for uncertain calls. Changed inputs/settings require a new declared analysis; incompatible checkpoints are rejected.

## 4. Researchers interpret and freeze the codebook

Two actual researchers inspect `stage3/synthesis_workspace.html` (or the Markdown worksheet), original posts, outliers, topic words and naming ballots. The local workspace offers a visible topic-to-theme overview, a **Combine selected topics** control and an **existing theme** selector on each topic. Several topics can share one theme. Original topics, rationales and draft definition text remain intact; changing a decision clears the review confirmations. The workspace keeps drafts separate from completed human review, provides definition fields and both researchers' notes, and exports a JSON decision record. Extend close reading when needed. No theme is approved automatically.

After both researchers actually complete the review, import their exported record:

```bash
python scripts/import-synthesis.py --config research-config.json --review TopicLLM-human-synthesis.json --output-config research-approved.json
```

This checks the evidence hashes and temporal design, writes the agreed map/codebook, and binds actual approval to those artifacts. Use the resulting configuration for subsequent stages. For a manual workflow, document definitions, grouping rationale and disagreements and save the completed map as `stage3/theme_map.csv`.

Create a JSON codebook with a `themes` object mapping each approved name to its definition, inclusion/exclusion rules and examples, plus a `decision_rule` for choosing one primary theme. Set `themes` and `codebook_path` in the configuration. The residual is exactly `The text does not fit into any of these themes`.

```bash
# Only after these people have actually completed the review:
topicllm --profile research --config research-config.json --record-review --reviewers "Actual researcher" "Actual second researcher"
```

The record binds source, date windows, assignments, naming, map and codebook. It records an actual attestation; executing a command does not prove someone reviewed the evidence. An agent must never fabricate it.

## 5. Annotate without model suggestions

Agree sample sizes before evaluation. The agreed application plan uses 100 development and 250 held-out posts per researcher. Evaluation is drawn first as a simple random sample without replacement from the complete target. Development sampling excludes all exact evaluation texts. No IDs or exact text appear in both sets.

```bash
python scripts/prepare-annotations.py --config research-approved.json --output runs/annotations --development-n 100 --evaluation-n 250
```

With a frozen codebook, this creates standalone local HTML interfaces and blank CSVs. If samples were already drawn, use the same output folder with --render-only to add the approved codebook without resampling. Complete development annotation and freeze the selected classifier before opening evaluation labels. Each researcher works independently without predictions, saves backups, and exports completed labels. Keep evaluation labels unavailable to prompt tuning and classifier selection.

```bash
python scripts/prepare-annotations.py --config research-approved.json --output runs/annotations/development_labels.csv --reviewer-exports reviewer-one-development.csv reviewer-two-development.csv
```

The merge retains both original labels and leaves disagreements blank for actual adjudication. Repeat for evaluation. Set `development_csv` and `benchmark_csv` to the adjudicated files, and `annotation_manifest` to the generated `sampling_manifest.json`. The transfer workflow checks the exact sampled IDs, target population, original text and both reviewer identities. Record actual annotation review with `--record-annotations PATH --reviewers ...`; do not certify generated labels.

For a joint review screen in your fork, render the unresolved merged file:

```bash
python scripts/prepare-adjudication.py --config research-approved.json --source runs/annotations/development_labels.csv --phase development --output development-adjudication.html
```

Both researchers discuss the disagreements using the frozen codebook. The local screen preserves the matching labels, shows both original answers, requires a consensus label and rationale for each difference, and exports a CSV only after both actual human confirmations. It supplies no suggested resolution. Save a draft if the discussion requires a codebook revision; record and approve that revision separately. The 250-post evaluation set remains outside development.

Check the returned export before recording the actual annotation attestation:

```bash
python scripts/prepare-adjudication.py --config research-approved.json --source runs/annotations/development_labels.csv --phase development --check development-adjudicated.csv
```

This checks original labels, notes, source text, frozen sample IDs, codebook hashes and completion fields. It does not automatically certify human work or run classification. Use the exported file as `development_csv`. For held-out adjudication after classifier selection, use `--phase evaluation` and the separately merged evaluation file.

## 6. Develop, evaluate, then accept

Development selects the higher-agreement Boolean or LLM classifier (LLM on a tie). Validation assesses only that frozen choice on the holdout. The phases run separately.

The published application completed evaluation at 70% agreement and failed its declared acceptance criteria. Its principal investigator explicitly authorized a **demonstration-only exception** to illustrate corpus classification with the unchanged model. This is not the default research path and does not establish validity. `demonstration_exception_path` identifies an actual researcher decision bound to the failed report, frozen classifier specification, annotation hash, exact target selection and cumulative spending ceiling. `demonstration.py` rejects changed evidence, excess spending, significance tests or a claim of validated status. Stage 5 labels the output as unvalidated model-assigned shares. An agent must never create this exception without the investigator’s explicit decision. The application’s record is [available here](docs/data/trump/campaign/demonstration_exception.json).

Individual human labels, adjudication notes and evaluation predictions are private. Released reports include aggregate confusion counts and per-theme performance. A fork can reproduce the mechanics and check aggregate calculations; it must supply its own independently collected annotations to repeat the human validation. Keep local annotation files outside the public checkout, and review release contents before publishing.

```bash
topicllm --profile research --config research-config.json --stages 4 --stage4-action development --plan
topicllm --profile research --config research-config.json --stages 4 --stage4-action development --budget-usd YOUR_APPROVED_TOTAL
# Only after selection is frozen and evaluation annotations are complete:
topicllm --profile research --config research-config.json --stages 4 --stage4-action validate --budget-usd YOUR_APPROVED_TOTAL
```

Inspect agreement, κ, per-theme support/precision/recall, confusion counts and individual errors. The minimum gate is agreement strictly >0.85, positive support and nonzero recall for every substantive theme. Researchers must also judge whether the errors are acceptable for the question. Revisions after evaluation require a fresh held-out sample; rare-category diagnostic samples cannot silently replace probability-sample accuracy.

After both researchers accept the observed performance:

```bash
topicllm --profile research --config research-config.json --record-validation-review --reviewers "Actual researcher" "Actual second researcher"
topicllm --profile research --config research-config.json --stages 4 --stage4-action classify --plan
topicllm --profile research --config research-config.json --stages 4 --stage4-action classify --budget-usd YOUR_APPROVED_TOTAL
topicllm --profile research --config research-config.json --stages 5
```

## 7. Report overall presidential prevalence

Resolve all errors first. `stage5/theme_counts.csv` reports each theme's numerator, common denominator and share, including zero-count themes and the residual. Classification must exhaust exactly the 26,239 target IDs. Campaign discovery exclusions do not alter that denominator.

The primary application reports overall shares only: `periods={}` and `run_pairwise_tests=false`. These are classifier-assigned shares of archived posting events, conditional on the codebook and measured errors. In the recorded demonstration they remain explicitly unvalidated. The residual measures use of the fallback label; it can combine content outside the codebook with classification errors, so it does not establish that substantive themes were absent. The shares do not measure public opinion or causal effects.

## Evidence and verification

Retain source and ordered-ID hashes, configuration and execution-source hashes, dependencies, model revisions, stopwords, exclusions, every candidate, selected model and rationale, ballots, actual interpretations, codebook, independent labels, adjudication, classifier selection/evaluation/acceptance, final classifications, counts and the API ledger. Load only trusted fitted-model pickles in the recorded environment.

For another corpus, explicitly define its question, discovery/target windows, stopwords, coding framework and validation design. Generic Python configuration has no implicit temporal filter. The `trump-demo` CLI profile supplies campaign/presidency windows for the bundled archive.

```bash
python -m pytest dtm_pipeline/tests -q
node --test tests/*.test.mjs
node scripts/verify-sources.mjs
python -m build --wheel --outdir dist_wheels
python scripts/package-release.py
node scripts/build.mjs
node scripts/check-site.mjs
python scripts/check-publication-privacy.py
python scripts/check-published-metrics.py
```

Rebuild the guide index after maintained documentation changes. Install the wheel outside the checkout and run quickcheck. Inspect the PDF and every responsive website surface. Software verification, source preservation and scientific validation are separate claims.
