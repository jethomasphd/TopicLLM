# Reproduce, inspect and adapt TopicLLM

The website is a working visual explanation. A fork or downloaded Python package is the intended environment for reproducible research and agent-assisted analysis. The preserved dissertation establishes what was reported; the maintained implementation and new synthetic runs are separately identified.

## 1. Install and run the free acceptance check

Use Python 3.11 or newer. The full discovery run recorded in this release used Windows and Python 3.12. Fork the repository, clone your fork, then:

```sh
python -m venv .venv
```

Activate with `.venv\Scripts\Activate.ps1` in PowerShell, or `source .venv/bin/activate` in bash/zsh. From the repository root:

```sh
python -m pip install ".[dev]"
topicllm --profile quickcheck --output-dir runs/quickcheck
```

Alternatively install the downloadable `topicllm_research-0.3.0-py3-none-any.whl`; the wheel includes the canonical synthetic data. It is a local distribution named `topicllm-research`, not a claim that a package has been published to PyPI.

Expected quickcheck: 5,872 classified rows, five prevalence rows, 15 comparisons, and all 15 one-decimal prevalence percentages matching the reported study table. This mode explicitly substitutes generator truth for classification, exercises the actual inference code and makes no model calls. It does not validate an LLM.

## 2. Give an agent an explicit task

Ask the agent to read `AGENTS.md`, this guide, `docs/protocol.json`, `AUDIT.md` and the revised methods. Provide the research question, input location, data-processing authorization and API spending ceiling. Have it inspect and plan before substantive execution. The agent may prepare review evidence and propose mappings; actual researchers approve the scientific decisions.

The intended sequence is **fork → verify → plan → discover → name → researcher review → validate → classify → estimate → export**. For the bundled synthetic acceptance run only, an explicitly labeled generator-based mapping replaces researcher review as a software fixture.

## 3. Run a full synthetic workflow

Install discovery dependencies:

```sh
python -m pip install ".[ml,dev]"
topicllm --profile synthetic-e2e --votes 20 --budget-usd 5 --max-api-calls 7000 --workers 6 --output-dir runs/synthetic-live --plan
```

Set `OPENAI_API_KEY` privately in your local environment, then repeat without `--plan`. The command uses your own API account. The website's operator gateway is for deployment verification and is not a public analysis backend.

This profile uses the exact bundled corpus, benchmark and stopwords. It performs 50 random discovery draws over ceilings 2–25, collects 20 independent naming calls per discovered topic, builds the review packet, and derives a synthetic-only topic map from the majority generator label of each discovered cluster. It evaluates both classifiers on all 250 benchmark records, scales the winner if the gate passes, and estimates prevalence and 15 period comparisons. The model's observed topic count remains unchanged. The seven-topic guided construction is a separate artifact.

Twenty votes are a disclosed software-validation budget. The historical naming budget was 5,000 per topic; set `--votes 5000` only after reviewing the much larger cost. The benchmark is 250 sampled corpus records, uses generator labels and includes only three Gaming examples. All texts share generator templates, and synthetic topic mapping uses generator truth across the corpus. It cannot establish human agreement or real-world performance.

Resume with the same output directory and unchanged settings. To reuse a completed discovery step, add `--discovery reuse`. The saved input/model hashes and discovery settings must match. The API budget includes previous attempts in that directory. Raising a budget requires an actual authorization; changing it does not reset recorded usage. Successful responses are cached by operation and input/settings fingerprint. Independent votes are never collapsed into one cached call. Only one process should own a run directory. Gateway retries use an operation fingerprint plus attempt number, so an explicit retry is distinct from duplicate delivery.

The backend disables SDK automatic retries and uses one recorded retry layer. Temporary failures may retry; billing errors stop. Failed or uncertain attempts retain a conservative reservation when provider usage is unavailable. API budget estimates use a dated model price schedule and UTF-8 input bounds; they are not a billing invoice. A new model requires reviewing the schedule.

## 4. Use a real research corpus

Create a JSON configuration using `examples/research-config.json` as a schema example. Set input/benchmark/stopword paths, theme names, periods, model identifier and output directory. Paths resolve from the command's working directory. Do not copy synthetic theme names into another field without researcher justification.

Python requires `tweet`; use stable unique `post_id` values, and ISO `date` values for period inference. Resolve blanks and duplicates explicitly before analysis. Prepare an independently annotated benchmark with `tweet,human_label`; ensure positive support for every theme and separate it from prompt tuning. Document any annotation disagreements and adjudication.

```sh
topicllm --config research.json --stages 1
topicllm --config research.json --stages 2,3 --budget-usd 5 --votes 20
```

Inspect `stage3/synthesis_worksheet.md`. After the primary and senior researchers review the evidence and agree, fill `theme_map_TEMPLATE.csv`, save it as `theme_map.csv`, and update the configuration taxonomy. Record the actual reviewers:

```sh
topicllm --config research.json --record-review --reviewers "Actual researcher one" "Actual researcher two"
topicllm --config research.json --stages 4,5 --budget-usd 5
```

The quoted names above are placeholders for instructions, not an approval record. Agents must not run the approval command with invented names. Stage 4 checks the review fingerprints and refuses the bundled synthetic benchmark for other input data. Human attestation does not replace independent review of the analysis or the appropriateness of its thresholds.

## 5. Inspect the artifacts

| Stage | Key outputs | What to assess |
|---|---|---|
| Discovery | `stage1/run_manifest.json`, `all_iteration_results.json`, `topics_for_naming.csv`, `best_model/parameters.json`, `best_model/fitted_model.pkl` | attempted/scored/failed candidates, observed topic count, outliers, selected model/input hashes |
| Naming | `stage2/naming_manifest.json`, `vote_log.csv`, `vote_tallies.csv`, `topic_names.csv`, `all_naming_attempts.jsonl` | all ballots and failures, normalization, modal share, synonyms and substantive ambiguity |
| Synthesis | `stage3/synthesis_worksheet.md`, `theme_map.csv`, `review_record.json` | evidence, mapping, actual review or explicitly synthetic fixture, bound hashes |
| Classification | `stage4/benchmark_predictions.csv`, `benchmark_report.json`, `classified_corpus.csv` | every raw response, per-theme support/precision/recall, gate, winner, missingness, retained IDs |
| Inference | `stage5/theme_counts.csv`, `prevalence_by_period.csv`, `ztest_results.csv` | counts and denominators, exclusions, later-minus-earlier direction, adjusted alpha, sparse cells |
| Run | `api_ledger.sqlite`, `api_usage.json`, `api_responses.json`, `synthetic_run.json`, `verification.json` | actual usage, completed/uncertain attempts, cached operations, pass/fail status and limitations |

The full model uses pickle; load only models you created or independently trust, in the recorded environment. Never load an untrusted downloaded pickle. Public validation downloads omit executable model serialization; the generating workflow retains it locally with its hash.

## 6. Verify code and sources

```sh
python -m pytest dtm_pipeline/tests -q
node scripts/verify-sources.mjs
pnpm install --frozen-lockfile
pnpm check
```

`dtm_pipeline/requirements-lock-windows-py312.txt` records the full tested ML environment. It is platform-specific. On other systems resolve compatible dependencies, record the resulting environment and assess changes in model outputs; a fixed seed does not guarantee cross-version or cross-platform numerical identity.

## Scope and release interpretation

The original private records, fitted model, LLM ballots and human benchmark are unavailable for privacy/IRB reasons. Synthetic calibration reproduces rounded reported percentages, not original observations or test statistics. Full synthetic validation establishes software behavior on this constructed dataset. The package does not implement LIWC sentiment analysis or Study 2 generalized structural equation modeling. Apparent source inconsistencies remain unchanged and are listed in `AUDIT.md` for author judgment.
