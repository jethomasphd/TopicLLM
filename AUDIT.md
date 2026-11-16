# TopicLLM sources and implementation provenance

Audit date: 16 November 2026. Source baseline: `16a2f53`.

## Source fidelity

The repository was inventoried and its dissertation, study papers, methods paper, supplements, data, code and website reviewed. The 304-page dissertation is authoritative. Study 1 occupies pages 148–179; Study 2 occupies pages 180–205. Existing standalone papers are reflowed editions, with front matter and references added. Body-text comparison after whitespace and quotation normalization matched Study 2; Study 1 had table reading-order differences.

The website now serves the full original PDF at chapter page anchors. Its PDF.js reader verifies the source hash before rendering, supports page navigation and zoom, and exposes selectable original text. It does not regenerate, transcribe or edit the authoritative chapter pages. `source-integrity.json` records the SHA-256 hashes of the dissertation, six existing preprint files and three archival code supplements. The build refuses changed protected sources and checks the served dissertation byte for byte. Checksums use original Git blob bytes from the baseline; `.gitattributes` preserves LF text endings across platforms. The synthetic generator also writes canonical LF CSVs, verified byte for byte against the repository.

The revised methods HTML and eight-page PDF are new editions. The earlier methods PDF and Word file remain available as archival documents. `scripts/render-methods.py` produces the new PDF from the HTML with ReportLab; its optional authoring dependencies are `reportlab`, `lxml` and `pypdfium2`. Inspect the rendered pages after editing.

## Topic discovery on different data

The dissertation reports seven observed topics, coherence 0.768, iteration 25, UMAP 15 neighbors / 4 dimensions / minimum distance 0.01, HDBSCAN minimum cluster size 20, and a maximum-topic setting of 23 (p. 163). Seven was not the configured ceiling.

The archived synthetic reference selected 20 topics with coherence 0.7896204. It contains additional delivery, social-promotion, recipe and background templates. These can form coherent lexical clusters. Browser preprocessing, embeddings, UMAP, clustering, merging and random-number generation also differ from Python BERTopic. An exploratory browser result near 22 is therefore not a rerun of the private historical study.

The default walkthrough maps known generator campaigns to seven explicitly assigned categories and the five reported themes. It calculates all 15 rounded prevalence percentages from 5,872 synthetic records, matching Table 3. Its period counts of 1,707 / 806 / 3,106, with 253 February records outside the comparison periods, are calibration choices. It claims no fitted coherence score, recovered historical ballots, human annotation or original denominators. Synthetic z statistics remain labeled synthetic.

## Implementation safeguards

- Failed, empty, truncated, ambiguous and unknown LLM responses cannot become valid substantive or residual classifications.
- Naming failures do not become votes. Python retains an append-only record of naming attempts and archives incomplete attempts before restarting a topic. Browser partial response records can be saved for audit; loading a saved record restores inputs and requires recomputation.
- Checkpoint fingerprints bind ordered inputs, topic words, taxonomy, prompts, decoding settings and model choice. Reordered or changed data cannot inherit old row-index labels.
- Browser upstream changes invalidate downstream results. Missing text, malformed CSVs, invalid dates, overlapping periods and unresolved classifications are rejected.
- Validation requires a nonempty benchmark, strict agreement above the chosen threshold, and positive support and nonzero sensitivity for every theme. Precision, sensitivity, agreement, Cohen's kappa and confusion counts are reported. These are minimum checks, not proof of adequacy for a research question.
- Browser z statistics use the same later-minus-earlier direction as Python. Zero variance is reported as unestimable. Counts, denominators, percentage-point changes, relative changes and sparse-cell warnings remain available.
- MiniLM loading failures stop discovery; hashed vectors require explicit selection. The browser is bounded to 6,000 documents.
- Python search records now retain failed and unscorable candidates, input hashes, effective stopwords and the observed dependency environment. It saves the full winning fitted model, its SHA-256 hash, topic assignments and parameters. The validated Windows / Python 3.12 dependency lock and a pinned MiniLM revision are included. Only load your own trusted pickle, in its recorded environment.

## Historical and synthetic evidence

The dissertation is the historical source of truth. The visual walkthrough is a teaching reconstruction on generated data, and the complete synthetic run is a separate measured software demonstration. Different corpora can produce different topic counts. Source files are preserved unchanged, and maintained implementations retain their own configuration and evidence. The public source guide explains these distinct purposes without presenting synthetic results as changes to the historical study.

## Hosting and data handling

The public website is a visual demonstration; a fork or installed Python package is the research execution environment. Cloudflare serves static assets, unchanged source readers and fixed synthetic OpenAI examples. The classification endpoint accepts fixed example IDs only. A separate research-guide endpoint accepts bounded questions and recent conversation about the public dissertation and software; it retrieves public source excerpts and provides source links. Visitor-selected models and research uploads are not accepted. Server credentials never reach browsers.

Atomic Durable Object reservations enforce the owner's $1 daily / $5 monthly public allowance, session/network caps, concurrency and idempotency. A separate one-time $5 budget governs synthetic validation. Uncertain calls retain reservations and storage errors fail closed. The operator route is paused after validation. Privacy, retention and operating procedures are documented in `DEPLOYMENT.md` and the website's data-handling page.

## Release verification

The complete synthetic discovery search ran 50 draws and all 1,200 planned candidate ceilings, recording scored and unscorable results. It selected 21 observed topics at ceiling 22, iteration 16, with c_v = 0.7961721. The fitted model reloaded with identical assignments. This measured result is retained separately from the seven-category guided reconstruction; coherence is not evidence of historical equivalence.

The live benchmark used all 250 generator-labeled examples. OpenAI agreement was 93.6% (kappa 0.9096), versus 92.0% for the Boolean classifier. The full workflow uses 20 naming votes per discovered topic, a disclosed synthetic-oracle mapping and the selected classifier. See `verification/synthetic-validation-2026-11-16.json` and the website's validation record for completed corpus results, candidate counts, per-class metrics, API usage and limitations. The benchmark has only three Gaming examples and is not a human-annotated validation sample.

The package and public controls have automated acceptance coverage, including source hashes, strict labels, row retention, inference boundaries, checkpoints, reviewer attestation, paid-call caching, atomic budgets, rollover, duplicate requests and storage failure. The final release record reports actual counts and CI outcomes. The wheel is also tested after installation outside the checkout. The revised PDF is rendered and visually inspected; original protected sources remain byte-identical.

The owner registered topicllm.dev, which is configured as the primary Cloudflare address. Real research requires independently annotated data and actual scientific review. The five-stage package does not implement LIWC sentiment analysis or Study 2 generalized structural equation modeling. Restricted original records remain unavailable for privacy/IRB reasons.
