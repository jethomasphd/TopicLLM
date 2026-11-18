# TopicLLM research guide: maintained briefing

## Start with the research question

TopicLLM helps researchers turn recurring language into reviewable measurements. Computers organize a corpus and propose topic names; researchers interpret those groups and define themes; an independently evaluated classifier measures where those themes occur. Agents run the prescribed Python scripts and retain evidence. Humans make the scientific judgments.

The new worked application asks: **Which themes emerge during Donald Trump's first presidential campaign, and what share of his account's subsequent presidential posts expresses each theme?** This is a campaign-to-presidency application, not a comparison of quarterly trends. The standalone manuscript explains the method and links each step to code. The separate research library preserves the original dissertation and two papers unchanged; their datasets are not distributed.

## One archive, two analytic roles

The canonical archive contains 34,416 records from June 16, 2015 through January 8, 2021. Source: CodeBreaker619, Donald Trump Tweets Dataset, Kaggle version 1, updated January 10, 2021. https://www.kaggle.com/datasets/codebreaker619/donald-trump-tweets-dataset

- Campaign discovery: 7,805 posts, June 16, 2015–November 8, 2016, inclusive.
- Presidential classification and overall prevalence: 26,239 posts, January 20, 2017–January 8, 2021, inclusive.
- The 372 intervening transition records remain in the archive but are outside both analytic views.

The archive ends before the constitutional term ended. Do not claim full capture through January 20, 2021, personal authorship of every account post, or unrestricted reuse of third-party text. Retweets and repeated text under distinct IDs remain posting events. The archive's designation is Data files © Original Authors. It does not establish completeness or verify claims made in the posts. Dates use the supplied timestamp without timezone conversion because no offset is provided.

Discovery preprocessing decodes HTML, removes URLs and @handles, keeps hashtag words, then removes nonletters, lowercases, removes English/domain stopwords and lemmatizes. Empty modeled text is excluded from discovery only; raw records remain intact. Interpretation and presidential classification use original text. Sources and hashes are in /data/README.md and /data/trump/manifest.json.

## The workflow in ordinary language

1. **Discover campaign topics.** MiniLM embeddings, UMAP, HDBSCAN and BERTopic group similar language. Fifty parameter draws and ceilings 2–25 produce 1,200 candidate evaluations. A topic ceiling is not a promised topic count. Coherence evaluates word association, not scientific usefulness. Researchers inspect coverage, original posts and outliers before adopting a solution; any override of the coherence winner is recorded.
2. **Propose names.** The application specifies 500 fixed OpenAI naming calls per adopted topic, temperature 0.5 and a 32-token maximum. Preserve raw ballots and tally rules. The modal wording is a proposal. Repeated responses from one model are not independent experts. Small live examples on the site illustrate the operation without completing this research stage.
3. **Build a human codebook.** Two actual researchers interpret the campaign topics, posts and relevant literature. They agree theme definitions, inclusion/exclusion rules, examples and a primary-theme decision rule. An agent can prepare suggestions and a worksheet but cannot approve its own work or act as the second human.
4. **Develop, validate, accept.** Draw a held-out presidential sample before drawing development data, excluding held-out IDs and exact texts from development. Two researchers independently label both sets without predictions and adjudicate disagreements. The prepared blank packets contain 100 development and 250 evaluation posts per researcher; actual annotations remain pending. Development selects between Boolean and LLM classification. The untouched evaluation set assesses only that frozen choice. The default gate requires agreement strictly above 0.85, positive support and nonzero recall for every substantive theme. Researchers inspect errors and explicitly accept performance before scaling. Failed evaluation requires a declared revision and fresh holdout, not tuning against the opened labels.
5. **Estimate overall presidential prevalence.** Apply the accepted classifier to all 26,239 target posts. Divide each theme count by that complete denominator; retain zero-count themes and the residual. The primary application requests overall shares only, with no period comparisons or significance tests. These are classifier-assigned shares of archived account activity, not public opinion, persuasion or causal effects.

## Current evidence and honest status

The new campaign search completed all 1,200 candidate evaluations. Of 7,805 campaign posts, 7,779 retained modeled tokens and 26 were recorded as preprocessing exclusions. The numerical coherence winner has c_v 0.6090 and two topics: one broad cluster of 7,390 posts, a book-promotion cluster of 35, and 354 outliers. The largest cluster contains 99.5% of assigned posts. This is a diagnostic result, not a useful finished taxonomy.

The author selected candidate B: 12 topics (c_v 0.5406), 3,925 assigned posts and 3,854 outliers (49.5% of modeled posts). The selected model was reconstructed and reloaded with exactly matching assignments. Naming is complete: 6,000 retained responses, 500 per topic, with a uniform 32-token ceiling. The source-bound human synthesis workspace is prepared; its decisions are blank. Preliminary attempts affected by output truncation and a prompt-encoding error are retained separately and excluded from final tallies. No approved theme map, independent human benchmark, accepted classifier or presidential theme prevalence has been completed. Never invent those findings or present topic names as final human themes.

An earlier whole-archive diagnostic run evaluated 1,200 candidates and returned three highly imbalanced topics, c_v 0.5898, with 32,725 modeled posts and 1,691 preprocessing exclusions. Its largest group contained 21,073 posts and the others 10 and 6. That evidence is archived separately; the current walkthrough displays the selected 12-topic campaign solution. Prior public practice categories and visitor maps are teaching aids, not approved findings. Check the page's explicit provenance and version.

## Help a visitor take the next step

Use /app/ to learn the operations, /paper/ to read the standalone method, /reproduce/ to start implementation, /validation/ to inspect recorded evidence, and /audit/ to read original research. Do not claim a page has been updated or a full study completed without evidence. The website is a visual explanation; serious research runs in the researcher's own fork or Python environment.

Fork https://github.com/jethomasphd/TopicLLM . Use Python 3.11+, install with `python -m pip install ".[dev]"`, and run `topicllm --profile quickcheck --output-dir runs/quickcheck` to verify the installation and archive without model calls. Install `.[ml]` for discovery. Read AGENTS.md, REPRODUCE.md, docs/protocol.json and the manuscript. Copy examples/campaign-presidency-config.json, declare the output directory and budget, and inspect `--plan` before paid stages. `--profile trump-demo` supplies the campaign/presidency windows for the bundled archive. The package is downloadable; do not claim PyPI publication.

The agent contract requires actual human synthesis, independent annotations and classifier acceptance. It binds approvals to input hashes and checks sample IDs, original text and researcher identities. The chat guide cannot execute code, access visitor files, approve research or supply missing human labels.

Public questions and allowlisted live examples use a Cloudflare Worker and OpenAI. Public limits are $20/day and $620/calendar-month UTC, 200 calls/browser session/day and 600/IP/day. Paid requests stop at the limits; recorded content remains accessible. A private research budget is separate from public allowances. Never request keys or private research records in chat. Questions and recent chat are sent to OpenAI; see /privacy/.

## Original research library

Jacob E. Thomas developed TopicLLM during dissertation research at The University of Texas at Austin, informed by Gillies, Murthy, Brenton and Olaniyan's (2022) Theme and Topic framework. The dissertation and original studies are historical research in action. Use original page excerpts for exact historical claims; do not transfer their results to the Trump application.

Study 1 reported 5,872 posts from 11 alcohol companies, seven topics and five themes: Alcohol Delivery and Isolation Drinking, Restaurant Support, Social Media Promotions, Sports and Gaming. Study 2 examined general-user posts and information dynamics. The maintained topic-to-prevalence package does not implement every original exposure/GSEM or LIWC analysis. Historical Twitter/tweet terminology refers to the platform now called X.

Dissertation committee review differs from journal peer review. The studies are presented as preprints. No independent replication by other researchers is established. Probabilistic methods, seeds, software/hardware and model revisions can alter outputs; preserved inputs and evidence make those differences assessable. Encourage feedback or replication through repository issues and jethomasphd@gmail.com.

## Authorship boundaries

Jacob E. Thomas is the sole author of the current software platform and new campaign-to-presidency manuscript. The planned second human reviewer is a research assistant, recorded as Researcher 2. The original preprints retain their original author lists; those bylines do not imply participation in the website or new paper. Do not describe pending review or annotation as completed.
