# Run TopicLLM with your agent

Start with the [Trump visual walkthrough](https://topicllm.dev/app/), then run the same method in your fork. The dissertation and study papers document prior applications; their datasets are not included. The tutorial uses one public corpus: 34,416 account posts from 2015-06-16 through 2021-01-08.

## 1. Install and verify

Use Python 3.11+ and a fresh environment. Clone or fork https://github.com/jethomasphd/TopicLLM . From the checkout:

```bash
python -m venv .venv
# Windows: .venv/Scripts/Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install ".[dev]"
topicllm --profile quickcheck --output-dir runs/quickcheck
```

A downloadable wheel also installs with `python -m pip install /path/to/topicllm_research-0.5.0-py3-none-any.whl`. PyPI publication is not assumed. quickcheck verifies hashes, 34,416 unique IDs, dates and flags; it makes no model or API calls. Record the commit and `python -m pip freeze`. The Windows/Python 3.12 ML lock documents the measured environment, not a universal lock for other platforms.

## 2. Discover topics

```bash
python -m pip install ".[ml]"
topicllm --profile trump-demo --plan
topicllm --profile trump-demo --output-dir runs/trump
```

The default runs Stage 1 only: 50 random configurations × topic ceilings 2–25. Embeddings run locally; the first run may download MiniLM and NLTK resources. The complete archive is the input. Empty modeled texts are logged and excluded from discovery only. Topic count and outlier share are results, never targets. Inspect all candidates and the winning model, not coherence alone. `--iterations 2` is a smaller declared exploration, not the published reference search.

## 3. Collect names and prepare the review

Configure `OPENAI_API_KEY` privately in your environment. Never paste keys into an agent chat or commit them. Decide the number of calls and a spending ceiling before execution. Twenty votes per topic are a small teaching run; the historical protocol used 5,000. More votes do not create independent human judgments.

```bash
topicllm --profile research --stages 2,3 --votes 20 --output-dir runs/trump --plan
# Replace the amount with your approved total ceiling, including resumed calls:
topicllm --profile research --stages 2,3 --votes 20 --output-dir runs/trump --budget-usd 5
```

The budget is an upper bound, not an expected charge. The default attempted-call ceiling is 10,000 across stages and resumed calls. A historical-size naming run or full Trump classification can exceed it: inspect `--plan`, then explicitly set `--max-api-calls` to your approved ceiling as well as the dollar budget. The local ledger tracks attempts, caches completed logical operations and retains conservative reservations for uncertain requests. Review `api_usage.json` and `api_responses.json`. Stop if inputs/settings change; use a new run directory rather than overwriting incompatible checkpoints.

## 4. Researchers interpret and validate

Read `stage3/synthesis_worksheet.md`, topic words, sampled posts and raw ballots. Two actual researchers use relevant domain literature to decide the themes. Fill `theme_map_TEMPLATE.csv`, save `theme_map.csv`, and document definitions, inclusion/exclusion rules and ambiguous cases. The agent must not approve the map.

Copy `examples/trump-config.json` to a research configuration and fill its `themes` array with the approved names. Supply `benchmark_csv` with independent human annotations (`tweet,human_label`; stable `post_id` recommended). Keep benchmark material separate from prompt tuning. The residual option is exactly `The text does not fit into any of these themes`. There is no bundled human benchmark for the Trump data.

```bash
# Only after the named researchers have actually reviewed and approved:
topicllm --profile research --config research-config.json --output-dir runs/trump --record-review --reviewers "Actual researcher name" "Actual reviewer name"
topicllm --profile research --config research-config.json --stages 4 --output-dir runs/trump --plan
# Set an independently approved ceiling for benchmark + possible corpus calls:
topicllm --profile research --config research-config.json --stages 4 --output-dir runs/trump --budget-usd YOUR_APPROVED_AMOUNT
```

Stage 4 benchmarks Boolean and LLM classifiers, chooses the higher agreement (LLM on a tie), and scales only if agreement is strictly >0.85 and every substantive theme has positive support and nonzero sensitivity. Inspect per-theme precision, recall and confusion counts; these minimum gates are not sufficient evidence for every research purpose. Repeatedly tuning against a held-out benchmark compromises its independence; collect a fresh evaluation set when needed. Full-corpus LLM classification can cost much more than the small naming exercise.

## 5. Estimate and interpret

```bash
topicllm --profile research --config research-config.json --stages 5 --output-dir runs/trump
```

Resolve missing, failed and ambiguous labels first. Review `prevalence_by_period.csv`, `ztest_results.csv`, counts, exclusions and denominators. Tutorial periods are campaign, transition and presidency through January 8, 2021; they exhaust the selected corpus but differ substantially in duration. The z-test assumes independent binomial observations and conditions on assigned labels. A single account's repeated, temporally dependent posts and retweets can violate that approximation. Report descriptive patterns, justify inferential alternatives and avoid causal claims.

## Your own corpus

Use `--input /path/to/corpus.csv`, a `tweet` column, unique stable IDs and valid dates if comparing time periods. This selects one input for discovery and classification. `--discovery-input` is optional only for a deliberately different research sampling design. Declare new stopwords, naming domain, periods, taxonomy, independent benchmark and budget in JSON. Do not inherit Trump-specific choices accidentally. `--mock-llm` exercises mechanics and labels outputs as mock; it cannot substitute for human review or scientific validation.

## Evidence to deliver

Retain source/input hashes, ordered IDs, source selection, effective preprocessing and stopwords, excluded texts, model revision, dependencies, seeds, all candidate scores/failures, assignments/outliers, the fitted model, raw naming ballots, synthesis decisions, review record, benchmark metrics, accepted labels and errors, period counts and tests, and API costs. Only load a fitted pickle that you trust. The downloadable reference evidence is linked from https://topicllm.dev/validation/ .

## Verify the recorded tutorial run

After discovery finishes, verify your own trusted model in the same ML environment:

```bash
python scripts/verify-trump-run.py --run runs/trump
```

This checks input/model hashes, the complete candidate search, an exact partition of source IDs and equality of saved assignments after model reload. It does not certify the scientific interpretation. Maintainers can rebuild the tutorial with `scripts/publish-trump-reference.py --run runs/trump`, followed by `scripts/build-tutorial-evidence.py`, `scripts/render-methods.py` and `scripts/build-guide.py`.

## Verify software changes

```bash
node --test tests/*.test.mjs
python -m pytest dtm_pipeline/tests -q
node scripts/verify-sources.mjs
python -m build --wheel --outdir dist_wheels
python scripts/package-release.py
node scripts/build.mjs
node scripts/check-site.mjs
```

Install the built wheel in a fresh environment outside the checkout and rerun quickcheck. Source preservation and software checks are separate from independent scientific validation.
