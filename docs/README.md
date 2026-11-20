# Find your way through TopicLLM

TopicLLM is a research workflow for turning a collection of text into human-defined themes and testing how reliably those themes can be measured. The worked example follows Donald Trump’s public Twitter posts from his 2015 campaign into his first presidency. The original dissertation and two study papers remain a separate, unchanged research library.

| Your next step | Start here |
|---|---|
| Get oriented | [Meet the dataset](https://topicllm.dev/data/) and [explore the five stages](https://topicllm.dev/app/) |
| Understand the scientific method | [Standalone methods paper](https://topicllm.dev/paper/) |
| Give an agent a concrete research task | [Execution guide](../REPRODUCE.md), [agent contract](../AGENTS.md), [machine-readable protocol](protocol.json) |
| Inspect the actual example | [Recorded evidence](https://topicllm.dev/validation/), [data card](data/README.md), [campaign configuration](../examples/campaign-presidency-config.json) |
| Develop or host the software | [Package guide](../dtm_pipeline/README.md), [deployment guide](../DEPLOYMENT.md), [contributing](../CONTRIBUTING.md) |
| Read the original research | [Research library](https://topicllm.dev/audit/) and [protected source manifest](../source-integrity.json) |

## Repository map

| Location | Responsibility |
|---|---|
| `dtm_pipeline/` | Python analysis stages, provenance checks and local human review interfaces |
| `examples/` | Explicit configurations and examples for an agent or researcher |
| `docs/` | Published website, manuscript source, data cards and public aggregate evidence |
| `docs/data/trump/corpus.csv` | Canonical public text corpus; the package includes a verified copy for installed use |
| `docs/data/trump/campaign/` | Recorded campaign discovery, approved codebook and aggregate evaluation/application evidence |
| `docs/paper/index.html` | Maintained standalone manuscript; the PDF is generated from this source |
| `docs/preprints/` | Downloadable papers; protected originals are listed in the source manifest |
| `docs/guide/knowledge.md` | Maintained briefing for the source-grounded website guide |
| `worker/` | Cloudflare API, guide retrieval, quotas and public-service controls |
| `scripts/` | Data preparation, publication builders, packaging and verification commands |
| `tests/` | Python and JavaScript behavioral tests |
| `.github/workflows/` | Cross-platform package and publication checks |

Local outputs such as `runs/`, build directories and private credentials are not part of the public source. Individual human annotations, adjudication notes and post-level evaluation predictions remain private. Public aggregate confusion counts support independent metric checks.

## Know what each record means

**Maintained documentation** explains the current software. **Recorded evidence** describes what actually ran, including its original software versions, parameters and decisions. Updating the release does not rewrite that provenance or make an earlier classifier more accurate. The original publications are preserved byte for byte.

The demonstration retained 12 themes, but its classifier matched only 70% of the 250 held-out reference labels and failed the declared acceptance criteria. Its full-corpus results are **unvalidated model-assigned shares**. Software checks verify execution and arithmetic; they do not substitute for scientific validation.

Interpretation uses **two-pass human theme review**. Annotation uses **two independent human coding passes**, each completed by a separate human coder, followed by adjudication. A coding agent executes the scripts and prepares evidence; it cannot supply either human pass or scientific approval.

## Keep generated surfaces synchronized

Follow [DEPLOYMENT.md](../DEPLOYMENT.md) for the complete release sequence. The welcome letter, evidence page, guide index, manuscript PDF and downloadable package have explicit builders. Edit their maintained sources first, rebuild, and verify source integrity, aggregate arithmetic, privacy, links, the installed package and the rendered pages before publishing.
