<p align="center"><a href="https://topicllm.dev"><img src="docs/assets/topicllm-mark.svg" width="84" alt="TopicLLM: text grouped into interpretable topics"></a></p>

# TopicLLM

### From language to evidence. Every step open.

**A research workflow for agents to execute and humans to understand, review and use.**

[Explore the live demonstration](https://topicllm.dev/app/) · [Read the methods](https://topicllm.dev/paper/) · [Run with your agent](REPRODUCE.md) · [Original Study 1 data](docs/data/README.md)

![Text becomes evidence through an inspectable research workflow](docs/assets/research-workflow.svg)

What is a large collection of posts talking about? How does that conversation change? TopicLLM finds groups of similar language, asks an LLM to propose names, and helps researchers turn those groups into meaningful themes. After independent validation, a classifier can label the corpus and estimate theme prevalence across time.

The agent handles computation, files and the evidence trail. Researchers decide what the themes mean, review validation and interpret the findings.

## A question that became an open method

TopicLLM grew out of dissertation research at **The University of Texas at Austin** on alcohol companies’ social media communication during COVID-19. It connects computational topic discovery with researcher-led interpretation, informed by the [Theme and Topic framework](https://arxiv.org/abs/2210.00707). The website is an invitation to understand the method; the repository is a starting point for you and your agent to test and extend it.

The dissertation studies received committee review. The study editions and methods are preprints, and the methodology has not yet been independently replicated by other researchers. The software checks and demonstration make specific evidence inspectable; scientific validation remains work for the research community.

**[Read Jacob’s welcome letter →](https://topicllm.dev/welcome/)**

## The actual study, ready to explore

The demonstration uses **original Study 1 alcohol-brand data**: **5,872 records from 11 brands**. The data and configuration are included in the package.

This is an **illustrative modern rerun**, not a promise of identical historical outputs. Topic models and LLMs include probabilistic steps. A fresh run can group or label some posts differently, especially when the random seed, model, or software version changes.

Walk through the five stages, search the study posts, collect OpenAI naming votes and inspect live classifications. Dissertation findings and new demonstration outputs are labeled where they appear.

## Start in minutes

Fork and clone this repository, then create and activate a Python 3.11+ environment:

```sh
python -m venv .venv
# PowerShell: .venv\Scripts\Activate.ps1
# bash/zsh: source .venv/bin/activate
python -m pip install ".[dev]"
topicllm --profile quickcheck --output-dir runs/check
```

The free quickcheck verifies the bundled data and setup. It makes no model or API calls.

To rerun discovery:

```sh
python -m pip install ".[ml,dev]"
topicllm --profile study1-demo --output-dir runs/study1 --plan
topicllm --profile study1-demo --output-dir runs/study1
```

The first run may download the embedding model and NLP resources. Discovery is local and makes no paid OpenAI calls. An [installable wheel and source archive](https://topicllm.dev/reproduce/) are also available.

## Give your agent a method

> Read AGENTS.md, REPRODUCE.md and docs/protocol.json. Verify the original Study 1 inputs. Run discovery in a new output directory. Explain the resulting topics and outliers, retain the evidence, and prepare the next steps and their costs for my review. Do not invent human labels, approvals or historical outputs.

| Stage | Agent executes | Researcher reviews |
| --- | --- | --- |
| Discover | Embeddings, UMAP, HDBSCAN and coherence search | Sampling, topic structure and coverage |
| Name | Independent LLM calls and vote tallies | Whether labels describe the underlying posts |
| Synthesize | Evidence packet and proposed theme map | Two researchers approve interpretation |
| Classify | Benchmark comparison, then corpus labeling | Independent annotations and per-theme performance |
| Estimate | Counts, prevalence and proportional tests | Denominators, assumptions and scientific meaning |

[REPRODUCE.md](REPRODUCE.md) provides exact commands and handoffs. [AGENTS.md](AGENTS.md) defines the execution contract. [protocol.json](docs/protocol.json) connects the method to machine-readable settings.

## Evidence you can inspect

The [demo record](https://topicllm.dev/validation/) shows the selected topics and model coverage, with complete run artifacts available to download. The dissertation supplies the reported study findings. Topic models and LLMs can vary across runs; retain the inputs, settings and outputs when adapting the method.

[Methods](https://topicllm.dev/paper/) explain the research decisions. [Technical data documentation](docs/data/README.md) specifies the inputs. [Source checksums](source-integrity.json) protect the original papers and supplements.

The maintained package covers the topic-to-prevalence workflow. Research classification requires an independent human benchmark. Study 2 user data, LIWC sentiment analysis and Study 2’s exposure-index/GSEM analysis are outside this package.

## Repository map

| Path | Purpose |
| --- | --- |
| `dtm_pipeline/` | Installable Python workflow |
| `docs/data/study1/` | Original Study 1 release and recorded discovery |
| `docs/` | Website, methods and research guide |
| `worker/` | Server-side OpenAI gateway and atomic usage accounting |
| `examples/` | Research configuration examples |
| `tests/`, `dtm_pipeline/tests/` | Software and data-integrity checks |
| `scripts/` | Build, source verification and release tooling |

The live demo has [shared service limits](https://topicllm.dev/privacy/). Full research runs use your own credentials and declared budget. Keep keys out of prompts and version control.

Code: MIT. Documentation and original author-created materials: see [LICENSE-CONTENT.md](LICENSE-CONTENT.md). Third-party brand text is not relicensed by those licenses. Cite the dissertation, methods and software using [CITATION.cff](CITATION.cff).
