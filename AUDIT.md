# TopicLLM publication and implementation audit

Audit date: 16 November 2026. Source baseline: `16a2f53`.

## Source fidelity

The repository was inventoried and its dissertation, study papers, methods paper, supplements, data, code and website reviewed. The 304-page dissertation is authoritative. Study 1 occupies pages 148–179; Study 2 occupies pages 180–205. Existing standalone papers are reflowed editions, with front matter and references added. Body-text comparison after whitespace and quotation normalization matched Study 2; Study 1 had table reading-order differences.

The website now serves the full original PDF at chapter page anchors. Its PDF.js reader verifies the source hash before rendering, supports page navigation and zoom, and exposes selectable original text. It does not regenerate, transcribe or edit the authoritative chapter pages. `source-integrity.json` records the SHA-256 hashes of the dissertation, six existing preprint files and three archival code supplements. The build refuses changed protected sources and checks the served dissertation byte for byte. Checksums use original Git blob bytes from the baseline; `.gitattributes` preserves LF text endings across platforms. The synthetic generator also writes canonical LF CSVs, verified byte for byte against the repository.

The revised methods HTML and seven-page PDF are new editions. The earlier methods PDF and Word file remain available as archival documents. `scripts/render-methods.py` produces the new PDF from the HTML with ReportLab; its optional authoring dependencies are `reportlab`, `lxml` and `pypdfium2`. Inspect the rendered pages after editing.

## The topic-count discrepancy

The dissertation reports seven observed topics, coherence 0.768, iteration 25, UMAP 15 neighbors / 4 dimensions / minimum distance 0.01, HDBSCAN minimum cluster size 20, and a maximum-topic setting of 23 (p. 163). Seven was not the configured ceiling.

The archived synthetic reference selected 20 topics with coherence 0.7896204. It contains additional delivery, social-promotion, recipe and background templates. These can form coherent lexical clusters. Browser preprocessing, embeddings, UMAP, clustering, merging and random-number generation also differ from Python BERTopic. An exploratory browser result near 22 is therefore not a rerun of the private historical study.

The default walkthrough maps known generator campaigns to seven explicitly assigned categories and the five reported themes. It calculates all 15 rounded prevalence percentages from 5,872 synthetic records, matching Table 3. Its period counts of 1,707 / 806 / 3,106, with 253 February records outside the comparison periods, are calibration choices. It claims no fitted coherence score, recovered historical ballots, human annotation or original denominators. Synthetic z statistics remain labeled synthetic.

## Research-integrity corrections

- Failed, empty, truncated, ambiguous and unknown LLM responses cannot become valid substantive or residual classifications.
- Naming failures do not become votes. Python retains an append-only record of naming attempts and archives incomplete attempts before restarting a topic. Browser partial response records can be saved for audit; loading a saved record restores inputs and requires recomputation.
- Checkpoint fingerprints bind ordered inputs, topic words, taxonomy, prompts, decoding settings and model choice. Reordered or changed data cannot inherit old row-index labels.
- Browser upstream changes invalidate downstream results. Missing text, malformed CSVs, invalid dates, overlapping periods and unresolved classifications are rejected.
- Validation requires a nonempty benchmark, strict agreement above the chosen threshold, and positive support and nonzero sensitivity for every theme. Precision, sensitivity, agreement, Cohen's kappa and confusion counts are reported. These are minimum checks, not proof of adequacy for a research question.
- Browser z statistics use the same later-minus-earlier direction as Python. Zero variance is reported as unestimable. Counts, denominators, percentage-point changes, relative changes and sparse-cell warnings remain available.
- MiniLM loading failures stop discovery; hashed vectors require explicit selection. The browser is bounded to 6,000 documents.
- Python search records now retain failed and unscorable candidates, input hashes, effective stopwords and the observed dependency environment. It saves the full winning fitted model, its SHA-256 hash, topic assignments and parameters. The validated Windows / Python 3.12 dependency lock and a pinned MiniLM revision are included. Only load your own trusted pickle, in its recorded environment.

## Source discrepancies preserved for author review

| Source | Issue |
|---|---|
| p. 164 / Table 3 | Restaurant pre-to-post change is reported as −30.8%; displayed percentages are 1.9% and 1.7%. |
| p. 164 | Sports z = 0.083 and p = 0.41 do not agree under a two-sided normal test. |
| p. 164 / Table 3 | Gaming relative change has a negative sign despite 1.1% increasing to 1.6%. |
| p. 191 / Table 4 | Text reports 704 brand tweets; the displayed brand counts sum to 703. |
| Appendix 1 | Final-fit code refits an unseeded model without retaining the selected topic ceiling. The maintained implementation retains the scored candidate instead. |

None of these discrepancies was corrected inside a source paper. The revised methods and website audit explain them separately.

## Hosting and data handling

One Cloudflare Worker serves static assets and the same-origin OpenAI gateway. Provider keys stay in server secrets. The gateway validates tasks and input limits, requires a research access code, limits requests per IP, pins the configured model, rejects incomplete responses, and returns model/request metadata. Calls use `store:false`; this does not assert zero provider retention. No raw corpus or credentials are logged by the application.

The initial access model is a controlled research deployment. A shared code and approximate per-location rate limit are not per-user quotas or a global spending cap. A broad public service needs individual identity, enforceable budgets, operational monitoring and appropriate data-processing arrangements. See `DEPLOYMENT.md` for deployment and domain instructions.

## Verification and remaining release work

The automated suite passes 25 Python tests and 14 JavaScript/Worker tests. The built site passes 104 local link and asset checks. Coverage includes source hashes, synthetic prevalence, invalid labels, missing text, CSV structure, inference boundaries, checkpoint reuse, and Worker access controls, input limits, response metadata and truncation. The browser walkthrough was exercised through calculation; a real MiniLM run processed all 5,872 synthetic documents with one search draw and seven candidate ceilings in about 96 seconds. It found eight topics at the deliberately bounded test ceiling of eight, with coherence 0.5731. Ten mock naming votes per topic then completed and handed off to the researcher worksheet. This is a software smoke test, not historical model verification.

The revised PDF was rendered and inspected. The site was deployed to https://topicllm.jethomasphd.workers.dev using the connected Cloudflare account. Desktop and phone layouts were checked, and the Cloudflare deployment bundle passed a dry run. No paid OpenAI call was made. A real Python BERTopic run also processed all 5,872 records, with one search draw and ceilings 2–8. It selected seven observed topics at ceiling 8, coherence 0.6425 and outlier share 25.8%. This deliberately bounded smoke test is not the dissertation result or a full 50-draw optimization. The selected model was serialized and reloaded with identical assignments. The run took about 198 seconds after imports; the validated dependency lock is `dtm_pipeline/requirements-lock-windows-py312.txt` and the embedding revision is `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`.

Before calling this a public production release: configure OpenAI and access secrets; run a small live synthetic naming/classification check; verify the deployed source readers and exports; choose and connect the domain; complete author review of the revised manuscript. The five-stage pipeline does not implement the dissertation's LIWC sentiment analysis or Study 2 generalized structural equation model. Restricted original records remain unavailable for privacy/IRB reasons.
