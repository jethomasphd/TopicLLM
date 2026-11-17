# One corpus: Trump account posts, 2015–2021

The hands-on TopicLLM tutorial uses **34,416 posts from June 16, 2015 through January 8, 2021**, inclusive. The dissertation and its two studies are separate historical research examples. Their datasets are not included in this release.

## Source and selection

Source: CodeBreaker619, *Donald Trump Tweets Dataset*, Kaggle, version 1, updated January 10, 2021. <https://www.kaggle.com/datasets/codebreaker619/donald-trump-tweets-dataset>

From the 56,571-row source CSV, retain every record whose source date is on or after 2015-06-16; sort by timestamp then integer ID. The archive ends 2021-01-08 15:44:28. This covers campaign and first-term account activity through the archive's endpoint, not through January 20. No language, sentiment, political topic or engagement filter is applied.

There are 34,416 unique IDs, no blank raw texts, 9,852 retweets, 1,092 records flagged deleted, and 343 repeated-text events beyond the first occurrence. Retweets and repeated text are retained as distinct posting events, not deduplicated into authored statements. The archive may omit posts; counts describe this file, not a claim of complete account history.

`trump/corpus.csv` is the single input for discovery and later research classification. `post_id` is a string identifier; preserve it exactly. `tweet` preserves the source text, including HTML entities. `date` is YYYY-MM-DD; `timestamp` retains the original timestamp without conversion. The source file supplies no timezone offset; selection uses its calendar dates without conversion. `is_retweet`, `is_deleted`, `is_flagged`, `device`, `favorites` and `retweets` preserve the source values. Engagement counts are archive snapshots, not current totals. Flags are archival metadata, not independently verified assessments.

## Modeling choices

The modeling copy decodes HTML entities, removes URLs and @handles, replaces nonletters with spaces, lowercases, tokenizes, removes NLTK English stopwords plus the six terms in `stopwords.txt`, and lemmatizes. Hashtag words remain after punctuation removal. The raw text is unchanged. Empty modeled texts are excluded from discovery and recorded explicitly; the source corpus retains every selected post. URL/handle removal is a declared domain adaptation of the historical preprocessing.

The six added tokens are `rt, https, http, co, amp, realdonaldtrump`. No candidate, policy, opponent or ideological terms are removed. Retaining retweets preserves account amplification behavior; a research sensitivity analysis can separately examine non-retweets with its own declared input hash.

Illustrative periods: campaign (2015-06-16–2016-11-08; 7,805 posts), transition (2016-11-09–2017-01-19; 372), presidency through archive end (2017-01-20–2021-01-08; 26,239). These exhaustive boundaries describe posting events. Unequal durations, dependence within a single account, retweets and changing platform use limit statistical interpretation.

## Verify or rebuild

`topicllm --profile quickcheck --output-dir runs/quickcheck` verifies the declared hashes and coverage. `trump/manifest.json` records source hash, exact selection, counts and output hashes. Rebuild from the upstream `tweets.csv` with:

```bash
python scripts/prepare-trump-data.py --source /path/to/tweets.csv
```

Discovery outputs are measured model results, not human annotations. The site provides small live examples and visitor-authored draft synthesis; research classification requires researcher-approved themes and an independent benchmark. There is no pre-approved Trump research taxonomy.

## Live examples from the same corpus

The live lab uses 1,024 evenly spaced chronological source rows, including the first and last records, plus three seeded samples from each recorded topic. Duplicate IDs are removed. This is a lightweight view of the same corpus, not another analysis population. `live-examples.json` preserves the selected source text and IDs; the complete source remains available in `corpus.csv`. Six broad practice categories illustrate classification mechanics. They are not researcher-approved themes or benchmark labels.

## Attribution and scope

Kaggle's designation is **Data files © Original Authors**. This project preserves that attribution and does not grant an MIT or CC BY license to third-party tweet text. Follow the source's applicable terms. Historical posts may contain offensive or false statements; inclusion is not endorsement or fact verification. The tutorial studies language and account activity, not voter attitudes, public opinion, or causal effects.
