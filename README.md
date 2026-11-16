<div align="center">

<img src="docs/assets/topicllm-mark.svg" width="56" height="56" alt="TopicLLM mark">

# TopicLLM

### From language to evidence. Every step open.

**Reproducible topic modeling for public-health research.**  
Discover structure, interpret it with people, and measure what changes.

[**Explore the platform**](https://topicllm.dev) · [**Try the visual demo**](https://topicllm.dev/app/) · [**Fork + reproduce**](https://topicllm.dev/reproduce/) · [**Read the method**](https://topicllm.dev/paper/)

[![Research and source integrity checks](https://github.com/jethomasphd/TopicLLM/actions/workflows/check.yml/badge.svg)](https://github.com/jethomasphd/TopicLLM/actions/workflows/check.yml)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-142c36?style=flat-square)](pyproject.toml)
[![Code: MIT](https://img.shields.io/badge/Code-MIT-076b57?style=flat-square)](LICENSE)
[![Release 0.3.0](https://img.shields.io/badge/Release-0.3.0-142c36?style=flat-square)](https://topicllm.dev/validation/)

<img src="docs/assets/text-to-evidence.jpg" width="1100" alt="Conceptual artwork: language fragments collect into themes and flow into measurements. This illustration is not a data visualization.">

<sub>Language → structure → evidence. Conceptual artwork; measured results are linked below.</sub>

</div>

TopicLLM connects **BERTopic discovery, democratic LLM naming, researcher-led interpretation, benchmarked classification and prevalence estimation** in one inspectable workflow. It was developed from dissertation research on alcohol marketing during COVID-19, with a maintained Python implementation and a fully synthetic demonstration corpus.

**The website makes the method visible. Your fork or Python environment is where research happens.** Give an agent the protocol, retain the evidence, and keep scientific decisions with actual researchers.

## Choose your starting point

| You want to… | Start here |
|---|---|
| **Understand the method** | Explore the [visual demonstration](https://topicllm.dev/app/) and [interactive conceptual model](https://topicllm.dev/#method), then try a fixed live OpenAI example. |
| **Run with an agent** | [Fork the repository](https://github.com/jethomasphd/TopicLLM/fork), open your fork in your coding agent, and give it the task below. [AGENTS.md](AGENTS.md) defines its research boundaries. |
| **Use Python directly** | Run the offline quickcheck below, or install the [downloadable wheel](https://topicllm.dev/downloads/topicllm_research-0.3.0-py3-none-any.whl). Follow [REPRODUCE.md](REPRODUCE.md) for complete runs. |
| **Evaluate the evidence** | Read the [revised methods](https://topicllm.dev/paper/), [measured validation](https://topicllm.dev/validation/), [source audit](AUDIT.md) and unchanged dissertation chapters. |

## One chain. Five inspectable stages.

![Five-stage conceptual model: discover, name, researcher synthesis, benchmarked classification, and prevalence estimation. Each stage retains evidence.](docs/assets/research-workflow.svg)

1. **Discover** — MiniLM embeddings, UMAP, HDBSCAN and c-TF-IDF; coherence ranks candidates across a 50-draw search with 24 topic ceilings per draw.
2. **Name** — Independent LLM queries propose topic names. Retain every ballot and failure; inspect the modal name and disagreement.
3. **Synthesize** — Two researchers review the evidence and approve a theme map. The agent prepares the review packet and pauses for their decisions.
4. **Classify** — Compare Boolean and LLM classifiers with independently annotated research examples. Assess every theme before scaling a passing classifier.
5. **Estimate** — Count labels within defined periods; retain denominators, exclusions, prevalence, proportional z-tests and Bonferroni adjustments.

The historical naming protocol used **5,000 votes per topic**. The budgeted synthetic acceptance run used **20**. Repeated queries do not remove model bias; coherence and agreement do not replace scientific judgment. [Method and limitations →](https://topicllm.dev/paper/)

## Get an inspectable result first

Use **Python 3.11+**. Fork the repository, clone your fork, and open its directory. To evaluate the upstream code directly:

```sh
git clone https://github.com/jethomasphd/TopicLLM.git
cd TopicLLM
python -m venv .venv
```

Activate with `.venv\Scripts\Activate.ps1` in PowerShell or `source .venv/bin/activate` in bash/zsh, then:

```sh
python -m pip install ".[dev]"
topicllm --profile quickcheck --output-dir runs/quickcheck
```

**Expected:** 5,872 synthetic rows → five themes → 15 comparisons, with all 15 rounded prevalence targets matched. The quickcheck uses generator labels and the actual inference code. **It makes no API calls and does not evaluate an LLM.** Inspect the files in `runs/quickcheck`.

The [wheel](https://topicllm.dev/downloads/topicllm_research-0.3.0-py3-none-any.whl) includes the synthetic data and runs without a source checkout. It is a downloadable distribution; no PyPI publication is claimed.

## Give your agent a research contract

Copy this into your coding agent after opening your fork:

```text
Read AGENTS.md, REPRODUCE.md, docs/protocol.json, AUDIT.md and the methods.
Run the offline synthetic quickcheck before changing anything.
Verify protected source hashes; record the exact commit and environment.
Prepare a plan for my corpus, including exclusions, settings and API cost.
Work only within my approved budget. Retain raw responses and checkpoints.
Assemble the Stage 3 review packet and stop for actual researcher decisions.
Never invent human annotations, reviewer identities or historical results.
Validate on an independent benchmark and report every theme's performance.
Export the complete audit record before making scientific claims.
```

The intended sequence is **fork → verify → plan → discover → name → researcher review → validate → classify → estimate → export**. Approval is bound to the evidence by hash. Changed inputs cannot silently inherit old approvals or row-index labels.

[Reproduction guide](REPRODUCE.md) · [Agent instructions](AGENTS.md) · [Machine-readable protocol](docs/protocol.json) · [Research configuration example](examples/research-config.json)

## What has actually been validated?

The recorded **full synthetic workflow** completed all five stages on 5,872 generated records. Its evidence is downloadable and independently inspectable.

| Recorded result | Measurement |
|---|---|
| Discovery | **1,200** candidate ceilings; **21 observed topics** selected at cᵥ = **0.7962** |
| Naming | **420** live ballots, 20 per discovered topic |
| Benchmark | **93.6%** OpenAI agreement with generator labels; **92.0%** Boolean agreement, on 250 examples |
| Corpus and inference | All **5,872** rows labeled with IDs preserved; **15** period comparisons |
| API accounting | **$2.477165** conservatively accounted against an approved **$5** ceiling |
| Source integrity | **10** archival files verified byte for byte |

**This is software acceptance on constructed data.** The benchmark is sampled from the synthetic corpus, shares templates, and has only three Gaming examples. Its labels and synthesis map come from the generator. These results do not establish human agreement, independent generalization or historical numerical replication.

| Evidence | What it means |
|---|---|
| **Dissertation** | Seven observed topics synthesized into five themes. The dissertation is the historical source of truth. |
| **Guided website reconstruction** | Seven explicitly assigned categories; all 15 reported rounded prevalence percentages match **by construction**. |
| **New full synthetic run** | Unconstrained discovery selected 21 topics. Live predictions and prevalence differences are retained as measured. |

[Inspect the validation](https://topicllm.dev/validation/) · [Download run evidence](https://topicllm.dev/validation/synthetic-validation-2026-11-16.zip) · [Machine-readable results](verification/synthetic-validation-2026-11-16.json)

Automated checks cover Python behavior, public-service controls, source hashes and built-site links. CI installs the wheel outside the checkout on **Windows and Ubuntu, with Python 3.11 and 3.12**. The full ML run has a separately recorded Windows/Python 3.12 environment; lightweight CI does not establish cross-platform numerical equivalence.

<details>
<summary><strong>Run the complete synthetic pipeline</strong></summary>

Install discovery dependencies and inspect a plan before making paid calls:

```sh
python -m pip install ".[ml,dev]"
topicllm --profile synthetic-e2e --votes 20 --budget-usd 5 --max-api-calls 7000 --workers 6 --output-dir runs/synthetic-live --plan
```

Set your own `OPENAI_API_KEY` privately in your environment, then repeat without `--plan`. The $5 parameter is a ceiling, not a guarantee that a new run will finish at the recorded cost. Successful calls are cached; uncertain attempts retain conservative reservations. Use a new output directory for changed inputs or settings. The generator-derived review fixture is explicitly synthetic and cannot authorize research data.

See [REPRODUCE.md](REPRODUCE.md) for research commands, actual reviewer attestations, independent benchmarks, dependency scope and stage artifacts.

</details>

## The source stays intact

The **304-page dissertation** is authoritative. Chapter readers serve the original PDF and verify its checksum before rendering. Existing PDF/Word preprints and archival supplements are preserved as received. The revised methods are a separately identified edition.

| Read | Original or revised edition | Preserved standalone editions |
|---|---|---|
| **Methods** | [Audited web edition](https://topicllm.dev/paper/) · [Revised PDF](docs/preprints/TopicLLM_Methods_Revised_2026-11-16.pdf) | [Earlier methods and audit](https://topicllm.dev/audit/) |
| **Study 1 · Alcohol marketing during COVID-19** | [Original Chapter 4, pp. 148–179](https://topicllm.dev/studies/1/) | [PDF](docs/preprints/Thomas_et_al_Paper1_Alcohol_Marketing_on_Twitter_During_COVID-19.pdf) · [Word](docs/preprints/Thomas_et_al_Paper1_Alcohol_Marketing_on_Twitter_During_COVID-19.docx) |
| **Study 2 · Alcohol information dynamics** | [Original Chapter 5, pp. 180–205](https://topicllm.dev/studies/2/) | [PDF](docs/preprints/Thomas_et_al_Paper2_Alcohol_Information_Dynamics_During_Crisis.pdf) · [Word](docs/preprints/Thomas_et_al_Paper2_Alcohol_Information_Dynamics_During_Crisis.docx) |

[Unchanged dissertation](THOMAS-PRIMARY-2025.pdf) · [Protected-source hashes](source-integrity.json) · [Source discrepancies for author review](AUDIT.md)

Standalone preprints are reflowed editions with added front matter, not byte-identical chapter files. Original posts, fitted model, naming ballots and human benchmark are unavailable because of privacy/IRB constraints. The [synthetic data card](docs/data/README.md) explains the replacement corpus. LIWC sentiment analysis and Study 2 structural equation modeling are outside this five-stage package.

## Find your way around

| Location | Purpose |
|---|---|
| [`dtm_pipeline/`](dtm_pipeline/) | Python implementation, configuration, synthetic generator and tests |
| [`AGENTS.md`](AGENTS.md), [`REPRODUCE.md`](REPRODUCE.md), [`docs/protocol.json`](docs/protocol.json) | Agent contract, execution guide and machine-readable workflow |
| [`docs/`](docs/) | Website, visual demo, source readers, methods and [synthetic data](docs/data/) |
| [`verification/`](verification/) | Recorded synthetic and deployed-service acceptance evidence |
| [`worker/`](worker/), [`DEPLOYMENT.md`](DEPLOYMENT.md) | Cloudflare/OpenAI gateway, atomic allowances and operating procedures |
| [`S1`](S1_bertopic_optimization.txt), [`S2`](S2_democratic_topic_naming.txt), [`S3`](S3_llm_classification.txt) | Protected archival code supplements, separate from the maintained implementation |

Public live OpenAI calls accept **fixed synthetic examples only**: ten calls/session/day, thirty/IP/day, and **$1/day / $5/month** site-wide. The walkthrough remains available when the live allowance is exhausted. Research data and credentials belong in the researcher's approved environment. [Data handling →](https://topicllm.dev/privacy/)

<details>
<summary><strong>Develop the website locally</strong></summary>

Use Node 22+, pnpm 11+ and an activated Python environment:

```sh
pnpm install --frozen-lockfile
python -m pip wheel . --no-deps --wheel-dir dist_wheels
python scripts/package-release.py
pnpm build
pnpm dev
```

Keep exactly one wheel in `dist_wheels`. The preview disables production host redirects locally. The build verifies protected sources. Run `pnpm check` and follow [DEPLOYMENT.md](DEPLOYMENT.md) before publishing. [Visual identity and artwork provenance](docs/assets/ARTWORK.md).

</details>

## People, citation and license

**Jacob E. Thomas, Dhiraj Murthy, Miguel Pinedo, Alexandra Loukas and Keryn E. Pasch**  
The University of Texas at Austin

> Thomas, J. E., Murthy, D., Pinedo, M., Loukas, A., & Pasch, K. E. (2026). *Coherence-optimized topic modeling with democratic large language model interpretation: A human-in-the-loop pipeline for public health surveillance of social media* [Preprint].

> Thomas, J. E. (2026). *TopicLLM: Coherence-optimized topic modeling with democratic large language model interpretation* [Computer software]. https://github.com/jethomasphd/TopicLLM

The revised methods are **not peer-reviewed**. Use [CITATION.cff](CITATION.cff) or the [website citation formats](https://topicllm.dev/#cite). DOIs will be added when deposited. Methodological questions: [jethomasphd@gmail.com](mailto:jethomasphd@gmail.com).

Code: **[MIT](LICENSE)**. Preprints, synthetic data, website text and documentation: **[CC BY 4.0](LICENSE-CONTENT.md)**.

<div align="center">

**Explore it. Fork it. Leave a result someone else can inspect.**

[topicllm.dev](https://topicllm.dev) · [Reproduce](REPRODUCE.md) · [Agent contract](AGENTS.md) · [Evidence](https://topicllm.dev/validation/)

</div>
