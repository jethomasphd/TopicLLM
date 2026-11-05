# TopicLLM

**Coherence-optimized topic modeling with democratic large language model interpretation:
a human-in-the-loop pipeline for public health surveillance of social media.**

Jacob E. Thomas, Dhiraj Murthy, Miguel Pinedo, Alexandra Loukas & Keryn E. Pasch ·
The University of Texas at Austin

**Website: <https://jethomasphd.github.io/TopicLLM/>** · [Instrument](https://jethomasphd.github.io/TopicLLM/app/) ·
[Methods preprint (web)](https://jethomasphd.github.io/TopicLLM/paper/)

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

## Preprints

| | Title | Files |
|---|---|---|
| Methods | *Coherence-Optimized Topic Modeling with Democratic Large Language Model Interpretation: A Human-in-the-Loop Pipeline for Public Health Surveillance of Social Media* | [PDF](docs/preprints/Thomas_et_al_Methods_Coherence-Optimized_Topic_Modeling.pdf) · [Word](docs/preprints/Thomas_et_al_Methods_Coherence-Optimized_Topic_Modeling.docx) · [web](docs/paper/index.html) |
| Study 1 | *Alcohol Marketing on Twitter During the COVID-19 Pandemic: Theme Identification, Prevalence Comparison, and Sentiment Analysis* | [PDF](docs/preprints/Thomas_et_al_Paper1_Alcohol_Marketing_on_Twitter_During_COVID-19.pdf) · [Word](docs/preprints/Thomas_et_al_Paper1_Alcohol_Marketing_on_Twitter_During_COVID-19.docx) |
| Study 2 | *Alcohol Information Dynamics During Crisis: A Longitudinal Analysis of Bidirectional Influence Between Alcohol Industry Marketing and User-Generated Content on Twitter During the COVID-19 Pandemic* | [PDF](docs/preprints/Thomas_et_al_Paper2_Alcohol_Information_Dynamics_During_Crisis.pdf) · [Word](docs/preprints/Thomas_et_al_Paper2_Alcohol_Information_Dynamics_During_Crisis.docx) |

The two study preprints reproduce Chapters 4 and 5 of the dissertation without modification:
[Thomas (2025)](THOMAS-PRIMARY-2025.pdf), *Alcohol Marketing on Social Media During the COVID-19
Pandemic: Historical Perspectives, Modern Evidence, and Future Regulation*, The University of Texas
at Austin.

## Repository

| Path | Contents |
|---|---|
| [`docs/`](docs/) | The website, served by GitHub Pages: landing page, [`app/`](docs/app/) (the in-browser instrument), [`paper/`](docs/paper/) (methods web edition), [`preprints/`](docs/preprints/), [`data/`](docs/data/) |
| [`dtm_pipeline/`](dtm_pipeline/) | The Python reference implementation: five stage scripts, orchestrator, configuration, demonstration-corpus generator, tests |
| `S1_…`, `S2_…`, `S3_…` | Archival supplements: the dissertation's Stage 1, 2 and 4 code exactly as executed (S2 and S3 use `openai==0.27.0`) |
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

Or use the instrument in a browser: open the website, or serve `docs/` locally with
`python3 -m http.server 8000 --directory docs` and visit <http://localhost:8000>.
(Opening the files with `file://` won't work, because the instrument uses ES modules and a Web Worker.)

## Data

**Demonstration corpus.** [`docs/data/`](docs/data/) holds an open, fully synthetic corpus. It has
5,872 posts from 11 fictional brands, a 250-post human-labeled benchmark, ground-truth themes, and
domain stopwords. It mirrors the structure of the published demonstration: per-brand volumes,
period sizes, and per-period theme prevalence calibrated to the published table. It contains no
real posts, accounts, or people. The pipeline and the instrument both use it by default. See the
[data card](docs/data/README.md).

**Dissertation data.** The source data for the published demonstration come from two places: brand
tweets recorded by the Prevention Research Lab Twitter Marketing Study, and user-generated tweets
from the Computational Media Lab COVID-19 Twitter Dataset. These data contain account-level
information and content governed by the platform's terms of service and by the agreements under
which they were collected, so they are not posted publicly. They are available from the
corresponding author (jethomasphd@gmail.com) on reasonable request for non-commercial research,
under a data use agreement consistent with those terms.

## Citation

> Thomas, J. E., Murthy, D., Pinedo, M., Loukas, A., & Pasch, K. E. (2026). *Coherence-optimized
> topic modeling with democratic large language model interpretation: A human-in-the-loop pipeline
> for public health surveillance of social media* [Preprint].

> Thomas, J. E. (2026). *TopicLLM: Coherence-optimized topic modeling with democratic large language
> model interpretation* [Computer software]. https://github.com/jethomasphd/TopicLLM

BibTeX for all five works (the three preprints, the software, and the dissertation) is on the
[website](https://jethomasphd.github.io/TopicLLM/#cite). DOIs will be added when the preprints are
deposited.

## License

Code is under the [MIT License](LICENSE). The preprints, demonstration corpus, website text, and
documentation are under [CC BY 4.0](LICENSE-CONTENT.md).
