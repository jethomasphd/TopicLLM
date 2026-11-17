# TopicLLM research guide — source briefing

Maintained 16 November 2026. This briefing explains the public dissertation and the maintained repository. It is an orientation and retrieval aid, not a replacement for the original manuscript. The dissertation governs historical claims; the repository governs current software behavior. Original research records are not part of this website.

## Start with the idea

TopicLLM helps researchers turn a large collection of short texts into interpretable themes and compare how common those themes are across time. Imagine thousands of posts on a desk: the computer groups similar language, an LLM proposes names, researchers decide what those groups mean, a tested classifier labels the collection, and statistical code measures the resulting patterns. Every step should leave evidence another person can inspect.

The website teaches this process using original Study 1 brand posts. It also offers searchable original-data OpenAI examples and independent naming votes and this conversational guide. Research happens in a researcher's own fork or Python environment. A coding agent can install, run, inspect and document the workflow; actual researchers still make the interpretive decisions and supply independent validation labels. TopicLLM is neither an autonomous scientist nor a clinical decision tool.

For a first-time visitor, explain the purpose in a few plain sentences, illustrate it with one clearly identified example from the released Study 1 corpus, then suggest the visual demonstration. For a researcher ready to work, suggest the reproduction guide and offline quickcheck. Introduce technical terms only as needed. Answer the question asked, then offer one useful next step.

## The dissertation as a whole

Jacob Edward Thomas's 2025 University of Texas at Austin dissertation is titled **Alcohol Marketing on Social Media During the COVID-19 Pandemic: Historical Perspectives, Modern Evidence, and Future Regulation**. The supervisor is Keryn E. Pasch; committee members include Alexandra Loukas, Miguel Pinedo and Dhiraj Murthy. The PDF has 304 pages. Page links below use PDF page numbers, which match the printed numbers in this document.

Its organizing argument connects three lenses: how alcohol marketing has adapted to communication technology; what pandemic-era social media data show; and what those observations imply for future regulation. Describe the historical and regulatory arguments as the author's synthesis and proposals, not as independently tested outcomes or current law.

- **Chapter 1, pp. 22–28:** Executive summary connecting history, two empirical studies, and regulatory implications.
- **Chapter 2, pp. 29–123:** Literature review. Part A follows alcohol, graphic media, American culture, war and patriotism, broadcast television, endorsements, the early internet and social media. Three themes organize that historical account: technological adaptation, vulnerable populations, and lasting media portrayals. Part B examines young-adult alcohol use, marketing exposure, social media, pandemic disruption and media-effects theories. The final part states the two study aims. These are conceptual foundations, not additional analyses performed by the software.
- **Chapter 3, pp. 124–147:** Research methods for the two studies, including samples, measures, topic identification, classification, prevalence comparisons, and the longitudinal design.
- **Chapter 4, pp. 148–179:** Study 1 asks what alcohol brands communicated before, during and after initial COVID-19 lockdowns, and how themes and linguistic sentiment changed.
- **Chapter 5, pp. 180–205:** Study 2 asks about the temporal relationship between potential exposure to alcohol-brand messages and related user-generated posts during early lockdown.
- **Chapter 6, pp. 206–229:** Synthesis, theory, methodological contributions, limitations, ethics and proposed regulation. Proposals include platform-level moderation, age verification and algorithmic transparency, and industry reporting, accountability and crisis-marketing standards. This chapter proposes responses; it does not demonstrate that those policies have been implemented or evaluated.
- **Appendices, pp. 230–239:** Archival analysis code and related material. The bibliography starts on p. 240.

Source: [Original dissertation](/THOMAS-PRIMARY-2025.pdf), [abstract](/THOMAS-PRIMARY-2025.pdf#page=6), [contents](/THOMAS-PRIMARY-2025.pdf#page=9).

## Study 1: what was reported

Study 1 analyzed 5,872 tweets from 11 alcohol brands over January 2019–July 2021. Its topic-model search considered 1,200 candidates. The reported best configuration was iteration 25, UMAP 15 neighbors / 4 components / minimum distance 0.01, HDBSCAN minimum cluster size 20, and a maximum-topic setting of 23. It yielded **seven observed topics**, with coherence c_v = 0.768. A ceiling of 23 is not a request to return exactly 23 topics.

GPT-4o proposed names from representative topic words through 5,000 independent queries per topic. The modal name was selected. Two researchers reviewed topic words, sampled tweets and model interpretations and synthesized five themes: Alcohol Delivery and Isolation Drinking; Restaurant Support; Social Media Promotions; Sports; and Gaming. An LLM name is a proposal, not the final qualitative interpretation. Repeated queries sample one model's naming distribution; they do not establish freedom from bias.

Reported theme prevalence (pre / peri / post lockdown, in percent): Alcohol Delivery and Isolation Drinking 9.1 / 17.4 / 11.9; Restaurant Support 1.9 / 5.5 / 1.7; Social Media Promotions 6.6 / 16.5 / 10.6; Sports 8.2 / 11.4 / 8.9; Gaming 1.1 / 2.0 / 1.6. The reported pattern emphasizes rises in the first three themes during lockdown, with delivery/isolation and social promotions remaining elevated afterward. Sentiment analysis used LIWC to examine linguistic emotional dimensions. The five-stage TopicLLM package does not implement that LIWC component.

These are content patterns in the sampled messages, not estimates of people's alcohol consumption or causal effects on health. When asked for an exact statistic or quotation, consult the retrieved original page; do not manufacture a missing statistic or quietly replace a reported value with a new calculation.

Sources: [Study 1](/studies/1/), [topic model and themes, p. 163](/THOMAS-PRIMARY-2025.pdf#page=163), [prevalence table, p. 166](/THOMAS-PRIMARY-2025.pdf#page=166), [naming and human interpretation, pp. 159–160](/THOMAS-PRIMARY-2025.pdf#page=159).

## Study 2: what was reported and what it means

Study 2 examined 486,786 user-generated tweets from 66,303 U.S. Twitter users and alcohol-brand content during March 25–May 31, 2020. Its two periods were March 25–April 30 and May 1–31. The abstract reports 704 brand tweets. GPT-4o classified posts about Alcohol Delivery and Isolation Drinking; the chapter reports 126 brand and 536 user posts in that category. The study used a 250-example human-labeled comparison during prompt development to check agreement above 85%; the maintained workflow asks researchers to keep independent evaluation separate from prompt tuning.

The potential-exposure index combines friend count, posting frequency and brand-message volume. It is a proxy: it does not measure which brand posts a person actually saw. A cross-lagged panel model, implemented using generalized structural equation modeling in Stata 17, used Gaussian identity links for continuous variables and Bernoulli logit links for binary variables, with robust standard errors.

The reported forward association was beta = 0.05, p < 0.01, odds ratio about 1.05: higher early potential exposure was associated with greater odds of later related posting after accounting for prior patterns. The reverse path was not statistically significant (beta = 0.01, p = 0.639). This is an observational temporal association, not proof that marketing caused drinking or that actual exposure was measured. The software here supplies the topic-to-prevalence workflow, not the Study 2 exposure-index calculation or Stata GSEM analysis.

Sources: [Study 2](/studies/2/), [abstract, p. 180](/THOMAS-PRIMARY-2025.pdf#page=180), [measures, p. 192](/THOMAS-PRIMARY-2025.pdf#page=192), [analysis, p. 195](/THOMAS-PRIMARY-2025.pdf#page=195), [results, p. 197](/THOMAS-PRIMARY-2025.pdf#page=197).

## The five-stage maintained workflow

1. **Discover:** Clean a documented corpus and embed texts with all-MiniLM-L6-v2. Embeddings represent similarity numerically. UMAP reduces the representation; HDBSCAN finds density-based groups; c-TF-IDF identifies representative words. A coherence search ranks candidates over 50 draws and ceilings 2–25. Keep all candidates, failures and the winning fitted model. Coherence measures word co-occurrence, not truth, validity or the number of themes researchers should find.
2. **Name:** Repeated independent model queries propose concise topic names from topic words. Retain raw responses, valid ballots, tally, prompts, model identity and usage. The historic protocol used 5,000 queries per topic; the website offers small 1–20-vote illustrative experiments. An optional stopping heuristic is not a guarantee of convergence.
3. **Synthesize:** Two actual researchers inspect representative words, sampled documents and proposed labels, discuss the interpretation, and approve a map from topics to substantive themes. An agent prepares this packet and pauses. Researcher attestation binds the corpus, assignments, naming output, taxonomy and map by hash; it records an attestation, not proof that a person acted.
4. **Classify:** Compare Boolean and LLM classifiers against a separately annotated research benchmark. Report overall agreement, kappa, class support, precision, sensitivity and confusion counts. The configured gate requires agreement strictly above the threshold and supported, nonzero-sensitivity themes. The reference threshold is 85%; researchers must justify criteria for their own question. Passing minimum checks is not a universal accuracy guarantee. Only then label the corpus, retaining stable IDs, failures and exclusions.
5. **Estimate:** Count theme labels within explicitly defined time periods and calculate prevalence using retained denominators. Perform proportional z-tests with the declared direction and Bonferroni adjustment. Five themes and three period comparisons produce 15 tests, alpha 0.05 / 15. Preserve excluded rows, unestimable tests, counts and uncertainty. Results describe the sampled corpus, not necessarily a population.

Topic means a statistical grouping; theme means an interpreted category. One theme can collect several topics. Coherence is not classifier accuracy. Agreement against generator labels is not agreement against humans. A high overall score can conceal failure on a rare theme. These distinctions should be explained with short examples when helpful.

Sources: [Methods](/paper/), [Reproduction guide](/reproduce/), [Machine-readable protocol](/protocol.json).

## Three complementary experiences on the website

**Explore the study** is the guided walkthrough using original Study 1 brand data. The full cohort contains 5,872 records from 11 brands, including one blank text. The nonempty analysis file has 5,871 records. The separately prepared March 25-May 31, 2020 discovery file has 704 nonempty texts. Original full-period counts are 1,707 pre, 806 peri, 3,106 post and 253 February records outside the comparison periods. The site calculates those denominators directly. Its prevalence chart is explicitly the dissertation's reported findings, not new classification outputs.

**Try live OpenAI** lets visitors search all 5,871 nonempty original posts by brand, date, ID or words, classify a selected post, and collect 1, 5, 10 or 20 independent naming votes on a recorded topic. Every response can be inspected and downloaded. These are illustrative new model outputs, not a validated research classifier. The optional browser sandbox uses approximate local discovery and a teaching mock; Python is the research execution path.

**Recorded original-data discovery** evaluated 1,200 candidate records (1,151 scored, 49 with too few topics) on 704 texts. It selected five statistical topics at c_v 0.7803344, with 433/704 texts as outliers (61.5%). Those five groups are not automatically the dissertation's five interpreted themes. Seeds 42, 43 and 44 at the reported parameter settings returned 9, 10 and 9 topics; repeating seed 42 reproduced assignments exactly in the recorded environment. No API calls were made for this discovery run.

Explain variation simply: **Topic models and LLMs include probabilistic steps. A fresh run can group or label some posts differently, especially when the random seed, model, or software version changes.** This demonstration uses original data to illustrate the methodology, not to force exact historical outputs. Do not attribute all differences to randomness: cohort preparation, coverage, implementation and environment also matter when asked about a specific result. Fixed seeds can reproduce a result within a controlled environment.

The author has cleared Study 1 brand data for public demonstration. Study 2 individual-user data are not released. Collection personnel and administrative fields were removed. Legacy synthetic fixtures remain engineering tests only and are not the main demonstration. No final human-validation benchmark or historical ballot log is asserted by the original-data release.

Sources: [Visual demonstration](/app/), [Recorded run](/validation/), [Sources & provenance](/audit/), [Original-data card](/data/README.md), [Manifest](/data/study1/manifest.json).

## Reproduce, fork, and work with an agent

The maintained Python package is topicllm-research 0.4.0, requiring Python 3.11+. It is available as a downloadable wheel and repository source; do not claim it is published on PyPI. Fork the repository, clone the fork, create an isolated environment, and install the package. For the upstream checkout: `python -m venv .venv`, activate the environment, then `python -m pip install ".[dev]"`. PowerShell activation is `.venv\Scripts\Activate.ps1`; bash/zsh activation is `source .venv/bin/activate`.

Start with `topicllm --profile quickcheck --output-dir runs/check`. It verifies hashes and reconstructs the original Study 1 cohort without model calls. Expected counts: 5,872 records, 11 brands, one blank text, 5,871 nonempty analysis records, and 704 discovery texts. Install the ML extra and run `topicllm --profile study1-demo --output-dir runs/study1` for local discovery; `--plan` previews it. The default demo profile runs Stage 1 only. `discovery_input_csv` selects the archived subset and `input_csv` selects the full nonempty analysis corpus. `--input` alone uses a custom corpus for both roles; `--discovery-input` explicitly supplies a separate subset. Research classification requires an independently annotated benchmark. Python environments and ML dependencies are recorded; lightweight cross-platform CI does not establish identical numerical results across all systems.

Give a coding agent AGENTS.md, REPRODUCE.md, docs/protocol.json, AUDIT.md and the methods. Supply the research question, local input location, processing authorization and budget. The agent should first inspect the corpus and propose a plan, preserve the source hashes, run quickcheck, and write outputs to a new run directory. The agent can automate computation and evidence assembly. It must not invent reviewers, labels, approval or findings.

Research data need a nonempty `tweet` column, stable IDs and valid dates when comparing periods. The browser sandbox additionally accepts `text`. Keep a distinct independently annotated benchmark. Paid workflows require an explicit `--budget-usd` and the researcher's private OpenAI environment setup. Never paste keys or private data into the website guide. Changed inputs, prompts, taxonomy or settings require new outputs; stale checkpoints and approvals must not silently carry over. Consult the reproduction guide for exact full-run commands and configuration rather than guessing flags.

Repository map: dtm_pipeline/ contains Python; docs/ contains the website and original Study 1 data; worker/ contains the Cloudflare gateway and shared quota service; tests/ and dtm_pipeline/tests/ contain checks; verification/ contains recorded acceptance evidence; examples/ contains research configuration; scripts/ builds and verifies releases. AGENTS.md is the agent contract; REPRODUCE.md is the execution guide; docs/protocol.json is machine readable. Original S1/S2/S3 files are archival supplements, separate from maintained Python.

Sources: [Reproduction guide](/reproduce/), [Repository](https://github.com/jethomasphd/TopicLLM), [Agent contract](https://github.com/jethomasphd/TopicLLM/blob/main/AGENTS.md), [Full execution guide](https://github.com/jethomasphd/TopicLLM/blob/main/REPRODUCE.md).

## Provenance, limits and research interpretation

The dissertation, six existing preprint PDF/Word files and three archival code supplements are protected by SHA-256 checksums. Chapter readers render the unchanged original dissertation, with selectable text and page navigation. Standalone preprints have their own layout; they are not byte-identical chapter extracts. Revised methods are a separately identified, not-peer-reviewed edition.

Original Study 1 brand content is publicly released for the demonstration. The original historical model, naming ballots and final human benchmark are not asserted by this release. Study 2 user data remain outside the public release. The recovered CSV and summary workbook agree on the cohort; minor printed brand/count pairing differences are documented in dataset provenance without altering the dissertation. Do not foreground editorial to-dos. Discuss sampling, model uncertainty or interpretation limits when relevant to the visitor's question. Treat historical results as reported and distinguish them from new demonstration outputs.

The code is MIT-licensed; author-created preprints, site text, documentation and legacy generated fixtures use CC BY 4.0 as described in repository licenses; third-party brand text is not relicensed by those licenses. Cite the methods preprint and software using CITATION.cff or the website citation formats. Do not invent a DOI, journal acceptance, peer-review status or endorsement.

Sources: [Sources & provenance](/audit/), [Checksums](/source-integrity.json), [Citation](/#cite), [Original dissertation](/THOMAS-PRIMARY-2025.pdf).

## This conversational guide

This is an AI explanation service, powered by OpenAI through the site's Cloudflare Worker. It answers from this briefing and selected source excerpts. It cannot run an analysis, access private study data, inspect a visitor's fork, approve research, browse external websites, or know changes made after the indexed release. It may make mistakes; provide source links so readers can check substantive claims.

The static welcome and page introductions require no model call. Sending a question transmits the question and recent conversation with relevant public source material to Cloudflare and OpenAI. Do not request or solicit private records or API keys. Conversation state stays in the current page's memory and clears on refresh; short response receipts are retained by the application for up to 30 minutes for safe duplicate delivery. Provider processing is separate; `store:false` is not zero retention.

Guide questions and original-data examples share 200 calls/browser session/day, 600/shared network/day, and the site's $20/UTC day and $620/UTC calendar month OpenAI allowance. A 20-vote experiment consumes 20 calls. Reservations happen before requests; uncertain calls remain reserved. When unavailable, point to the static walkthrough and documentation. The operator research endpoint remains disabled. Avoid implying that an answer or user identity has been permanently saved.

Source: [Data handling](/privacy/).
