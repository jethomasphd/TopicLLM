# TopicLLM

**Coherence-optimized topic modeling with democratic large language model interpretation:
a human-in-the-loop pipeline for public health surveillance of social media.**

Jacob E. Thomas, Dhiraj Murthy, Miguel Pinedo, Alexandra Loukas & Keryn E. Pasch ·
The University of Texas at Austin

**Website: <https://topicllm.jethomasphd.workers.dev/>** · [Visual demo](https://topicllm.jethomasphd.workers.dev/app/) ·
[Methods preprint (web)](https://topicllm.jethomasphd.workers.dev/paper/)

**The website is a visual demonstration. The Python package and your own fork are the research workflow.** Explore the method with synthetic data, then give an agent the repository's [reproduction contract](AGENTS.md), run the acceptance checks, and retain researcher control of interpretation and validation. Start with [REPRODUCE.md](REPRODUCE.md) or the [web guide](https://topicllm.jethomasphd.workers.dev/reproduce/).

TopicLLM turns large volumes of social media text into a small set of interpretable themes, and
those themes into prevalence estimates you can test. It runs in five stages:

1. **Discover.** BERTopic (MiniLM embeddings → UMAP → HDBSCAN → c-TF-IDF) runs under a randomized
   hyperparameter search of 50 draws × 24 topic solutions, or 1,200 planned candidate models. The model
   with the highest c_v coherence wins.
2. **Name.** A language model names each topic thousands of times, independently, and the modal
   label is adopted. Fragmented votes merit review; synonyms can also split votes.
3. **Synthesize.** Two researchers group topics into themes under the Theme and Topic system. Research decisions require explicit human approval. Synthetic-only tests use a labeled generator-based fixture.
4. **Classify.** Boolean and LLM classifiers are piloted against a human-labeled benchmark. The
   pipeline refuses to scale a classifier below the agreement threshold.
5. **Estimate.** Theme prevalence is computed by period and compared with proportional z-tests
   under Bonferroni correction.

Every stage writes an audit artifact that can be published with the findings: the hyperparameter
log, vote ballots and tallies, the theme map, the benchmark report, and the z-tests.

## Audited release

The default workbench is a **seven-topic synthetic reconstruction**. Its known campaign assignments reproduce the dissertation’s seven-to-five structure; recalculation matches all 15 rounded prevalence percentages. It is explicitly not an unsupervised recovery of the private study. Exploratory discovery reports its observed count. The full 50-draw validation found 21 topics at c_v = 0.7962; the seven-topic walkthrough remains a separate construction.

The unchanged dissertation is the source of truth. `source-integrity.json` protects it, all existing PDF/Word preprints and S1–S3. The website’s chapter readers point to the original pages. Revised methods are separate from preserved earlier editions.

- [Revised methods](docs/paper/index.html), [source audit](docs/audit/index.html), [agent protocol](docs/protocol.json)
- [Measured synthetic validation](https://topicllm.jethomasphd.workers.dev/validation/) with downloadable run evidence and API usage
- [Cloudflare deployment](DEPLOYMENT.md): static assets and a same-origin OpenAI Worker, with server secrets, access control and bounded requests
- Follow [the release build commands](DEPLOYMENT.md) before `pnpm check`, so Python downloads are present; `pnpm dev` previews locally.

The source corpus cannot be shared because of privacy and research-governance constraints. No original records, model weights, human benchmark or naming ballots are represented as recovered in this release.

## Preprints

| | Title | Files |
|---|---|---|
| Methods | *Coherence-Optimized Topic Modeling with Democratic Large Language Model Interpretation: A Human-in-the-Loop Pipeline for Public Health Surveillance of Social Media* | [Revised PDF](docs/preprints/TopicLLM_Methods_Revised_2026-11-16.pdf) · [web](docs/paper/index.html) · [audit and earlier version](docs/audit/index.html) |
| Study 1 | *Alcohol Marketing on Twitter During the COVID-19 Pandemic: Theme Identification, Prevalence Comparison, and Sentiment Analysis* | [PDF](docs/preprints/Thomas_et_al_Paper1_Alcohol_Marketing_on_Twitter_During_COVID-19.pdf) · [Word](docs/preprints/Thomas_et_al_Paper1_Alcohol_Marketing_on_Twitter_During_COVID-19.docx) |
| Study 2 | *Alcohol Information Dynamics During Crisis: A Longitudinal Analysis of Bidirectional Influence Between Alcohol Industry Marketing and User-Generated Content on Twitter During the COVID-19 Pandemic* | [PDF](docs/preprints/Thomas_et_al_Paper2_Alcohol_Information_Dynamics_During_Crisis.pdf) · [Word](docs/preprints/Thomas_et_al_Paper2_Alcohol_Information_Dynamics_During_Crisis.docx) |

For exact original wording, tables, figures and pagination, use the unchanged dissertation below. The older standalone study preprints are reflowed editions with added front matter; they are preserved as received, but are not byte-identical chapter files. The website’s study readers serve the original dissertation at Chapters 4 and 5:
[Thomas (2025)](THOMAS-PRIMARY-2025.pdf), *Alcohol Marketing on Social Media During the COVID-19
Pandemic: Historical Perspectives, Modern Evidence, and Future Regulation*, The University of Texas
at Austin.

The implementation and source audit are recorded in [AUDIT.md](AUDIT.md). Cloudflare setup and operating boundaries are in [DEPLOYMENT.md](DEPLOYMENT.md).

## Repository

| Path | Contents |
|---|---|
| [`docs/`](docs/) | The website, built for Cloudflare Workers with static assets: landing page, [`app/`](docs/app/) (the in-browser instrument), [`paper/`](docs/paper/) (methods web edition), [`preprints/`](docs/preprints/), [`data/`](docs/data/) |
| [`dtm_pipeline/`](dtm_pipeline/) | The Python reference implementation: five stage scripts, orchestrator, configuration, demonstration-corpus generator, tests |
| `S1_…`, `S2_…`, `S3_…` | Archival supplements: the dissertation's Stage 1, 2 and 4 code transcribed from the dissertation appendices (S2 and S3 use `openai==0.27.0`) |
| [`CITATION.cff`](CITATION.cff) | Citation metadata (GitHub's "Cite this repository") |

## Start here

```sh
git clone https://github.com/jethomasphd/TopicLLM.git
cd TopicLLM
python -m venv .venv
# Activate .venv for your shell, then:
python -m pip install ".[dev]"
topicllm --profile quickcheck --output-dir runs/quickcheck
```

This free check runs real inference on generator labels: 5,872 rows, five themes, 15 comparisons, all rounded prevalence targets matched. It does not evaluate a model. The installable wheel includes the synthetic data; no source checkout is required for this check.

For discovery, install `".[ml,dev]"`. For a complete live synthetic run, set your own `OPENAI_API_KEY` privately, inspect the plan, then execute:

```sh
topicllm --profile synthetic-e2e --votes 20 --budget-usd 5 --max-api-calls 7000 --workers 6 --output-dir runs/synthetic-live --plan
# Repeat without --plan after reviewing its cost and scope.
```

The synthetic profile runs all five stages with an explicitly generator-derived review fixture. Research runs require actual reviewer attestations and a separate annotated benchmark. API calls are budgeted, auditable and resumable. See [REPRODUCE.md](REPRODUCE.md) for research commands, artifact contracts and limitations, and [AGENTS.md](AGENTS.md) for the agent workflow.

The public website offers a free guided reconstruction and fixed anonymous OpenAI examples, capped at ten calls per browser session/day, thirty per IP/day and $1/day/$5/month site-wide. It does not accept arbitrary research text for hosted calls. The local browser sandbox uses a teaching mock. Research data and credentials stay in the researcher's approved environment.

For local site development, run `pnpm install --frozen-lockfile`, build the downloadable package with `python -m pip wheel . --no-deps --wheel-dir dist_wheels`, then `python scripts/package-release.py`, `pnpm build` and `pnpm dev`. Opening HTML with `file://` does not support modules or workers. See [DEPLOYMENT.md](DEPLOYMENT.md).

## Data

**Demonstration corpus.** [`docs/data/`](docs/data/) holds an open, fully synthetic corpus. It has
5,872 posts from 11 fictional brands, a 250-post generator-labeled synthetic benchmark, ground-truth themes, and
domain stopwords. It mirrors the structure of the published demonstration: per-brand volumes,
synthetic period sizes chosen for calibration, and rounded per-period theme prevalence matching the published table. It contains no
real posts, accounts, or people. The pipeline and the instrument both use it by default. See the
[data card](docs/data/README.md).

**Dissertation data.** Original brand and user-generated posts are restricted because of privacy and IRB obligations. They are not distributed or available for this demonstration. The website uses synthetic records only; it does not request or reconstruct private participant records.

## Citation

> Thomas, J. E., Murthy, D., Pinedo, M., Loukas, A., & Pasch, K. E. (2026). *Coherence-optimized
> topic modeling with democratic large language model interpretation: A human-in-the-loop pipeline
> for public health surveillance of social media* [Preprint].

> Thomas, J. E. (2026). *TopicLLM: Coherence-optimized topic modeling with democratic large language
> model interpretation* [Computer software]. https://github.com/jethomasphd/TopicLLM

BibTeX for all five works (the three preprints, the software, and the dissertation) is on the
[website](https://topicllm.jethomasphd.workers.dev/#cite). DOIs will be added when the preprints are
deposited.

## License

Code is under the [MIT License](LICENSE). The preprints, demonstration corpus, website text, and
documentation are under [CC BY 4.0](LICENSE-CONTENT.md).
