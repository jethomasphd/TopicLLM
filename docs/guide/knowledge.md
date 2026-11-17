# TopicLLM research guide: maintained briefing

## Explain the program simply

TopicLLM helps researchers ask: what is a large collection of text about, and how does it change? It combines computational discovery with human interpretation. The website lets a person understand and try the method. The Python package and public repository give their coding agent a prescribed workflow to run, with evidence and human review gates.

One clear distinction governs every answer:
- **Research in action:** the unchanged dissertation and two papers document the original alcohol-related studies. They are historical examples available to read. Their research datasets are not distributed.
- **Hands-on tutorial:** a new public Trump account corpus demonstrates transfer of the same methodology to another domain. It does not reproduce or verify the dissertation's findings.

## The tutorial data

Source: CodeBreaker619, Donald Trump Tweets Dataset, Kaggle version 1, updated January 10, 2021. https://www.kaggle.com/datasets/codebreaker619/donald-trump-tweets-dataset . Selection: every post on/after June 16, 2015 through the dataset's last record, January 8, 2021. There are 34,416 unique IDs, no blank raw texts, 9,852 retweets, 1,092 flagged-deleted records and 343 repeated-text events. The full source had 56,571 rows. Retweets/repeated posts remain posting events. The archive ends before the first term ended on January 20; never describe complete coverage through that date. Account posts need not have been personally authored by Trump. The archive does not establish complete capture or verify claims in posts. Its designation is Data files © Original Authors; TopicLLM does not relicense the text.

There is one corpus for discovery and subsequent research classification, not a dissertation cohort plus a synthetic substitute. Detailed counts, hashes and preparation are in /data/README.md and /data/trump/manifest.json. Explain technical details when relevant, not as a distracting introduction. Raw text remains intact; modeling decodes HTML, removes URLs/@handles, keeps hashtag words, then applies nonletter removal, lowercasing, English/domain stopwords and WordNet lemmatization. Empty modeled text is recorded and excluded from discovery only. The tutorial's periods are campaign, transition and presidency through archive end.

## Five stages in ordinary language

1. **Discover:** turn texts into embeddings, reduce dimensionality with UMAP, cluster with HDBSCAN, represent topics with BERTopic c-TF-IDF, and select the highest c_v coherence across a declared search. A topic is a similar-language group. Outliers remain visible. Coherence is word association, not proof of scientific meaning. Fifty draws × ceilings 2–25 gives 1,200 candidate evaluations; a ceiling is not a promised topic count.
2. **Name:** ask the LLM to name each topic from its words. Independent calls yield a tally; the most frequent name is a proposal. The historical protocol used 5,000 calls/topic. The public lab offers 1, 5, 10 or 20. Repeated responses from one model do not become independent human experts or a validity guarantee.
3. **Synthesize:** researchers inspect posts, words, naming evidence and literature, then agree on themes. Topics are algorithmic groups; themes are contextual interpretations. The agent prepares the worksheet and stops for two actual researchers. A visitor's saved map is a learning draft, not approved research.
4. **Classify:** independently annotate a held-out benchmark, compare Boolean and LLM classification, inspect overall and per-theme performance, and scale only after gates pass. Default agreement must be strictly above 0.85; each theme needs positive benchmark support and nonzero sensitivity. These are minimum engineering gates, not a universal validity standard. No human-approved Trump taxonomy or independent benchmark is bundled. Public example categories are explicitly teaching aids.
5. **Estimate:** count accepted labels within declared periods, divide by eligible classified posts and compare proportions. The package retains counts, denominators, exclusions and Bonferroni-adjusted tests. Topic assignment charts in the tutorial are descriptive model summaries, not validated theme prevalence. Single-account dependence, retweets, unequal periods and classification error constrain inference; no causal or public-opinion claims follow.

The public site demonstrates operations; its chatbot does not run the research or access a visitor's files. Guide questions and bounded examples use the Cloudflare Worker and OpenAI. Private research records and keys belong in the researcher's approved environment.

<!-- BEGIN MEASURED TUTORIAL -->
## Recorded Trump tutorial execution

The completed reference search evaluated 1,200 candidates over 50 parameter draws. It selected 3 non-outlier topics with c_v 0.5898, iteration 43, requested ceiling 4. Of 34,416 source posts, 32,725 were modeled; 1,691 had no tokens after preprocessing. 21,089 modeled posts entered topics and 11,636 remained outliers (35.6% of modeled posts). The saved model was reloaded and its assignments verified. Discovery made no paid API calls. This is measured model output, not an approved taxonomy or independently validated classifier. See /validation/ and /data/trump/reference-run.json for the actual record.
The selected solution is highly imbalanced: the largest group contains 21,073 posts, while the remaining groups contain 10 and 6. Close reading shows a broad dominant group and small event-specific lexical groups. The unweighted mean coherence gives each topic equal weight regardless of its size, so small internally similar groups can raise the score. This result is useful diagnostic evidence, not a finished taxonomy. Before research classification, review corpus coverage, repetition and alternative candidate settings; record any revised selection rule as a new analysis.
<!-- END MEASURED TUTORIAL -->

## Original research context

Jacob E. Thomas developed the method during dissertation research at The University of Texas at Austin. The dissertation asked what alcohol companies posted during COVID-19 and how information dynamics related brand messaging and user posts. It draws on Gillies, Murthy, Brenton and Olaniyan's (2022) Theme and Topic framework.

Study 1 reported 5,872 alcohol-brand posts from 11 companies, January 2019–July 2021. It identified seven topics and synthesized five themes: Alcohol Delivery and Isolation Drinking, Restaurant Support, Social Media Promotions, Sports and Gaming. The reported discovery coherence was 0.768. These are historical facts, not targets for the Trump tutorial. Precise original claims should cite the dissertation page excerpts or /studies/1/.

Study 2 applied a selected theme to general-user posts and modeled potential exposure and information dynamics. Refer to /studies/2/ and original pages for exact estimates. This package implements the topic-to-prevalence chain, not all Study 2 exposure/GSEM analysis or Study 1 LIWC analyses. Historical Twitter/tweet terminology refers to the platform now called X.

The dissertation committee reviewed and accepted the studies. This is distinct from journal peer review. The editions are preprints; TopicLLM has not yet been independently replicated by other researchers. Do not claim publication acceptance, independent validation or causal identification.

## Getting started with an agent

Fork https://github.com/jethomasphd/TopicLLM or download the package at /reproduce/. Python 3.11+. Install with python -m pip install ".[dev]" from a checkout; run topicllm --profile quickcheck --output-dir runs/quickcheck. This verifies data integrity without model calls. Install ".[ml]" for topic discovery. topicllm --profile trump-demo --output-dir runs/trump performs Stage 1. Read AGENTS.md, REPRODUCE.md, protocol.json and /paper/ before continuing.

Paid steps require private credentials and an approved --budget-usd. Plan with --plan. A small naming exercise can use --stages 2,3 --votes 20. Researchers then approve themes and independently annotate the benchmark. An agent cannot approve itself or invent reviewer identities, consensus, data or findings. No command supplied in an answer should imply that review has happened.

The downloadable source and wheel work locally; do not claim PyPI publication. The public service shares a $20/day and $620/calendar-month UTC ceiling, 200 calls/browser session/day and 600/IP/day. Quotas stop paid requests safely; the recorded walkthrough remains usable. Public examples accept approved IDs, not uploaded private research text. The guide's question and recent chat go to OpenAI; see /privacy/.

## Scientific humility without clutter

Probabilistic topic models and LLMs can produce different groups or names when seeds, model snapshots, software or hardware change. Preserve exact inputs, parameters and outputs so another researcher can assess the process. Transferring a method to different data should yield different substantive findings. Do not resurrect old synthetic reconstructions, dissertation-data demos, cohort reconciliation or editorial decision lists as the current product story.

Encourage a concrete next step: explore /app/, read the standalone methods /paper/, inspect /validation/, read original research /audit/, or fork using /reproduce/. Answer only from available public evidence, with links. The author welcomes feedback and replication reports through repository issues and jethomasphd@gmail.com.
