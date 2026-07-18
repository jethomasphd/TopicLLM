# TopicLLM

**Coherence-Optimized Topic Modeling with Democratic Large Language Model Interpretation**
— a human-in-the-loop pipeline for public health surveillance of social media (Thomas, 2026).

This repository carries the dissertation research from archive to instrument, in three layers:

| Layer | Where | What it is |
|---|---|---|
| **Preprint** | [`Coherence_Optimized_Topic_Modeling_Preprint.docx`](Coherence_Optimized_Topic_Modeling_Preprint.docx) · [PDF](docs/paper/Coherence_Optimized_Topic_Modeling_Preprint.pdf) · [HTML](docs/paper/index.html) | The methods paper distilled from the dissertation ([THOMAS-PRIMARY-2025.pdf](THOMAS-PRIMARY-2025.pdf)) |
| **Browser analysis service** | [`docs/`](docs/) | The full five-stage pipeline as a client-side web app — no server, no install; your data stays on your machine |
| **Python reference pipeline** | [`dtm_pipeline/`](dtm_pipeline/) | The maintained implementation of record (current OpenAI SDK), plus archival supplements S1–S4 |

## The five stages

1. **Coherence-optimized topic discovery** — BERTopic (MiniLM embeddings → UMAP → HDBSCAN →
   c-TF-IDF) under randomized hyperparameter search; the model maximizing c_v coherence wins,
   with a full audit trail.
2. **Democratic LLM interpretation** — each topic is named by plurality vote over thousands of
   independent LLM queries; the modal label is adopted and the ballots are published.
3. **Human-in-the-loop synthesis** — a structured two-researcher consensus protocol (Theme and
   Topic system) groups topics into themes; deliberately not automated.
4. **Validated corpus-scale classification** — Boolean-dictionary and LLM classifiers are piloted
   against a human benchmark; the pipeline refuses to scale below the agreement threshold.
5. **Inference** — proportional z-tests with Bonferroni correction, per-theme corpora for LIWC-22,
   and the Stata GSEM hand-off for cross-lagged panel models.

## The browser app (`docs/`)

A static single-page application implementing all five stages **entirely in the browser**:

- **Stage 1 in a Web Worker**: transformers.js runs all-MiniLM-L6-v2 locally
  (WebAssembly/WebGPU; ~25 MB one-time download), umap-js handles projection, and HDBSCAN
  (excess-of-mass), c-TF-IDF, and c_v coherence are faithful JavaScript ports.
- **Stages 2 & 4** call the LLM endpoint *you* configure — OpenAI-compatible or Anthropic —
  with your own API key, sent directly from your browser. A clearly-labeled keyless mock lets
  you exercise the whole workflow first. Prompts are verbatim from the paper's §2.7.
- **Stage 3** renders the two-researcher review packet as an interactive worksheet.
- Every stage exports the same audit artifacts the Python pipeline writes
  (`all_iteration_results.json`, `vote_log.csv`, `benchmark_report.json`, `ztest_results.csv`, …),
  individually or as one `pipeline_output.zip`.
- A synthetic demo corpus (600 documents + 250-document benchmark) is built in.

### Run it

- **Hosted (GitHub Pages):** in the repository settings, enable
  *Pages → Deploy from a branch → `main` (or this branch) → `/docs`*. The app then lives at
  `https://<user>.github.io/TopicLLM/`.
- **Locally:** `python3 -m http.server 8000 --directory docs` and open
  <http://localhost:8000>. (Any static file server works; opening `index.html` from `file://`
  won't, because the app uses ES modules and a Web Worker.)

The Python pipeline remains the implementation of record for publication-grade or large
(>~5,000-document) corpora; the app's Help tab documents the browser build's approximations.

## The preprint

`docs/paper/` holds the submission-ready PDF and a web edition (with Figure 1 and both tables).
Remaining author decisions before submission: the bracketed co-author line and the two
companion-manuscript citations in §3.

## The Python reference pipeline

See [`dtm_pipeline/README.md`](dtm_pipeline/README.md). Quickstart:

```bash
cd dtm_pipeline
pip install -r requirements.txt
python make_demo_data.py            # synthetic smoke-test corpus
python run_pipeline.py --stages 1   # discovery, no API cost
```

Supplementary files at the repository root: **S1–S3** are the archival dissertation
implementations (S2/S3 against `openai==0.27.0`, preserved as published); **S4** is the complete
LIWC-22 output for the five demonstration theme corpora.

## Citation

> Thomas, J. E. (2026). *Coherence-Optimized Topic Modeling with Democratic Large Language Model
> Interpretation: A Human-in-the-Loop Pipeline for Public Health Surveillance of Social Media.*
> Preprint.
