# Run TopicLLM with an agent

The website is an original-data illustration. A fork or installed Python package is the execution environment. Agents run the computation and retain evidence; researchers review interpretation and validation.

## 1. Install and verify the release

Use Python 3.11+ in an isolated environment. From your fork:

```sh
python -m pip install ".[dev]"
topicllm --profile quickcheck --output-dir runs/check
```

Expected: input hashes verified; the 5,872-record, 11-brand cohort reconstructed; one blank text; 5,871 nonempty analysis records; 704 archived discovery texts. No model or API calls. The wheel includes the same original-data files. `docs/data/README.md` describes their provenance.

## 2. Give the agent the contract

Read `AGENTS.md`, this guide, `docs/protocol.json`, `AUDIT.md`, and the methods. State the question, inputs and approved API budget. Use a fresh output directory for changed inputs or settings.

The intended sequence is **verify → discover → name → researcher review → validate → classify → estimate → export**. The current demonstration is an illustrative rerun of original Study 1 data, not exact historical output replication. Topic models and LLMs include probabilistic steps. Seeds, models and software versions can change groupings or labels.

## 3. Run local discovery

```sh
python -m pip install ".[ml,dev]"
topicllm --profile study1-demo --output-dir runs/study1 --plan
topicllm --profile study1-demo --output-dir runs/study1
```

This profile defaults to Stage 1, the 704-text discovery input, 50 draws, topic ceilings 2–25 and seed 42. The first run may download MiniLM and NLTK resources. It makes no paid API calls. `--iterations 2` is a clearly smaller exploratory run; it does not recreate the full search.

The configuration has two corpus paths: `discovery_input_csv` (704 archived texts) and `input_csv` (5,871 nonempty full-period records). Stage 1 hashes and uses the discovery input. Classification uses the analysis input. The full 5,872-row file retains the blank text for cohort accounting. Both corpora are bound into research review records. `display_text` is for reading only; discovery uses the archived `tweet` values without silent encoding repair.

For other data, `--input your.csv` uses that file for both discovery and classification unless `--discovery-input subset.csv` is explicitly supplied. A JSON config can declare the two inputs separately. Set an independent `--benchmark human_labels.csv` for research validation.

## 4. Name topics and prepare researcher review

Set `OPENAI_API_KEY` privately in your environment. Choose your own authorized ceiling; this example permits at most $5 of paid requests in this output directory:

```sh
topicllm --profile research --stages 2,3 --votes 20 --budget-usd 5 --output-dir runs/study1 --plan
topicllm --profile research --stages 2,3 --votes 20 --budget-usd 5 --output-dir runs/study1
```

Twenty votes illustrate the mechanism; the dissertation used 5,000 per topic. Every ballot is an independent operation, with raw responses and usage retained. The ledger accounts for attempted calls and safely resumes completed operations. The research workflow pauses for actual researcher interpretation at Stage 3.

Two researchers inspect the packet and complete `stage3/theme_map.csv`, configure the agreed themes, and record their own approval:

```sh
topicllm --profile research --config examples/study1-config.json --output-dir runs/study1 --record-review --reviewers "Actual Researcher One" "Actual Researcher Two"
```

Replace example names and configure the actual inputs; an agent must not invent names, annotations or approval. Changing inputs, topic evidence, labels or themes invalidates the review record.

## 5. Validate, classify and estimate

Create a separately annotated held-out benchmark with `tweet,human_label`. No final historical human benchmark is asserted by this release. Inspect support, precision, sensitivity, confusion counts and agreement. Declare criteria suitable for the question before scaling.

```sh
topicllm --profile research --config examples/study1-config.json --stages 4,5 --benchmark human_labels.csv --budget-usd 5 --output-dir runs/study1 --plan
```

After reviewing the plan and budget, repeat without `--plan`. The configured budget applies cumulatively to that run directory; adjust only with authorization. Classification requires the current researcher review record and a passing benchmark. Missing/invalid labels block inference. Period comparisons retain counts, denominators, exclusions, test direction and multiplicity adjustment.

## 6. Report what ran

Retain input and model hashes, environment, seeds, all candidate results, outliers, ballots, review records, benchmark metrics, raw/accepted labels, API ledger and statistical outputs. Published findings, recorded modern discovery and live demonstration responses must stay distinguishable. Repeating a seed within a fixed environment can repeat assignments; changing stochastic inputs or software can change outputs.

The recorded example selected five topics with 61.5% outliers. It illustrates the method and its coverage limitations; it does not assert recovery of the dissertation's five themes. The package does not implement LIWC or Study 2 GSEM.

## Engineering fixtures

Legacy generated files remain explicit regression fixtures. `--profile synthetic-quickcheck` exercises inference using generator labels. `--profile synthetic-e2e` uses the exact synthetic fixture and its explicitly nonhuman oracle mapping; it requires its own paid budget. Neither profile is the default demonstration or a source of human-validation evidence. Synthetic mappings can never authorize research classification.

## Deployment and checks

`npm test` checks browser and Worker contracts; `python -m pytest dtm_pipeline/tests -q` checks the package. `node scripts/verify-sources.mjs` protects original documents. Build the wheel, regenerate the guide index and revised methods PDF, package downloads, run the site build and link checks, then deploy with the existing Cloudflare configuration.

The public Worker accepts only released Study 1 example IDs and bounded guide questions. It enforces 200 session calls, 600 shared-network calls and a $20 site-wide allowance per UTC day, plus a $620 calendar-month ceiling. The operator research endpoint remains disabled. The website does not accept arbitrary private-corpus uploads for hosted model calls.
