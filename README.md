# TopicLLM

**Coherence-optimized topic modeling with democratic large language model interpretation:
a human-in-the-loop pipeline for public health surveillance of social media.**

Jacob E. Thomas, Dhiraj Murthy, Miguel Pinedo, Alexandra Loukas & Keryn E. Pasch ·
The University of Texas at Austin

**Website: <https://topicllm.jethomasphd.workers.dev/>** · [Instrument](https://topicllm.jethomasphd.workers.dev/app/) ·
[Methods preprint (web)](https://topicllm.jethomasphd.workers.dev/paper/)

TopicLLM turns large volumes of social media text into a small set of interpretable themes, and
those themes into prevalence estimates you can test. It runs in five stages:

1. **Discover.** BERTopic (MiniLM embeddings → UMAP → HDBSCAN → c-TF-IDF) runs under a randomized
   hyperparameter search of 50 draws × 24 topic solutions, or 1,200 candidate models. The model
   with the highest c_v coherence wins.
2. **Name.** A language model names each topic thousands of times, independently, and the modal
   label is adopted. A fragmented vote flags an ambiguous topic.
3. **Synthesize.** Two researchers group topics into themes under the Theme and Topic system. This
   stage is deliberately not automated.
4. **Classify.** Boolean and LLM classifiers are piloted against a human-labeled benchmark. The
   pipeline refuses to scale a classifier below the agreement threshold.
5. **Estimate.** Theme prevalence is computed by period and compared with proportional z-tests
   under Bonferroni correction.

Every stage writes an audit artifact that can be published with the findings: the hyperparameter
log, vote ballots and tallies, the theme map, the benchmark report, and the z-tests.

## Audited release

The default workbench is a **seven-topic synthetic reconstruction**. Its known campaign assignments reproduce the dissertation’s seven-to-five structure; recalculation matches all 15 rounded prevalence percentages. It is explicitly not an unsupervised recovery of the private study. Exploratory discovery reports observed topic counts, including the archived 20-topic synthetic result.

The unchanged dissertation is the source of truth. `source-integrity.json` protects it, all existing PDF/Word preprints and S1–S3. The website’s chapter readers point to the original pages. Revised methods are separate from preserved earlier editions.

- [Revised methods](docs/paper/index.html), [source audit](docs/audit/index.html), [agent protocol](docs/protocol.json)
- [Cloudflare deployment](DEPLOYMENT.md): static assets and a same-origin OpenAI Worker, with server secrets, access control and bounded requests
- `pnpm install --frozen-lockfile && pnpm check` checks JavaScript/Worker behavior and source integrity; `pnpm dev` previews locally

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

### Quickstart

```bash
git clone https://github.com/jethomasphd/TopicLLM.git
cd TopicLLM/dtm_pipeline
pip install -r requirements.txt
python run_pipeline.py --stages 1                  # discovery on the demonstration corpus, no API cost
python run_pipeline.py --stages 2,3 --mock-llm     # keyless dry run (set OPENAI_API_KEY for the real thing)
python run_pipeline.py --ground-truth --stages 5   # reference inference
python -m pytest tests -q
```

For the complete site, original source readers and Worker, run `pnpm install --frozen-lockfile`, `pnpm build`, then `pnpm dev` at the repository root. See [DEPLOYMENT.md](DEPLOYMENT.md).
(Opening the files with `file://` won't work, because the instrument uses ES modules and a Web Worker.)

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
