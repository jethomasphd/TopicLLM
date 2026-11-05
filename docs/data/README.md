# TopicLLM demonstration corpus — data card

A fully synthetic corpus for running the TopicLLM pipeline end to end, released
under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). It stands in for
the dissertation data, which are restricted (see *Access to the dissertation
data* below).

## Files

| File | Rows | Columns | Purpose |
|---|---|---|---|
| `demonstration_corpus.csv` | 5,872 | `post_id, brand, date, tweet` | The corpus (pipeline input) |
| `demonstration_benchmark.csv` | 250 | `post_id, tweet, human_label` | Human-labeled benchmark for the Stage 4 gate |
| `demonstration_ground_truth.csv` | 5,872 | `post_id, period, theme, campaign` | The theme and campaign behind every post |
| `demonstration_stopwords.txt` | — | comma-separated | Domain stopwords: brand terms and time words |

## What it mirrors

The corpus reproduces the *structure* of the published demonstration
(Thomas, 2025, Study 1), not its content:

- **Brands and volume.** There are 11 brands. The posts per brand match the dissertation's per-company counts
  (1,142 down to 117), and monthly volume follows the shape of its Figure 1.
- **Study periods.** Pre-pandemic (Jan 2019 – Jan 2020) has 1,707 posts. February 2020 has 253 posts
  and sits between periods. Peri-pandemic (Mar – May 2020) has 806 posts and post-pandemic
  (Jun 2020 – Jul 2021) has 3,106.
- **Themes.** The five published themes are Alcohol Delivery and Isolation
  Drinking, Restaurant Support, Social Media Promotions, Sports, and Gaming, plus
  "no theme". Their per-period counts are calibrated so that the ground-truth
  labels give the published prevalence table (pre / peri / post %):

  | Theme | Pre | Peri | Post |
  |---|---|---|---|
  | Alcohol Delivery and Isolation Drinking | 9.1 | 17.4 | 11.9 |
  | Restaurant Support | 1.9 | 5.5 | 1.7 |
  | Social Media Promotions | 6.6 | 16.5 | 10.6 |
  | Sports | 8.2 | 11.4 | 8.9 |
  | Gaming | 1.1 | 2.0 | 1.6 |

  Run Stage 5 on the ground truth (`python run_pipeline.py --ground-truth --stages 5`)
  and it returns this table, the published z statistics (each within 0.07), and the published
  pattern of Bonferroni-significant differences. A classifier's output comes close to the table only to the extent
  that the classifier agrees with the ground truth.
- **Campaigns.** The themes are carried by the kinds of campaigns the dissertation
  reports:
  - a delivery-app promotion, stay-home sipping, and a "little sunshine" campaign;
  - a restaurant-worker relief fund and takeout support;
  - living-room concert streams, "Howdy, neighbor" giveaways, and contests;
  - a virtual draft party, home sports challenges, and game day;
  - a charity gaming tournament on Twitch and game-night streams.

  Everyday brand posts make up the rest: recipes, holidays, launches, heritage,
  events, and miscellaneous chatter.
- **Benchmark.** The benchmark is 250 posts drawn at random from the lockdown months, when all five
  themes are most prevalent. Its labels are the ground truth.

## Reference run

[`reference_run/`](reference_run/) holds the outputs of a full reference run on
this corpus, so you can check your own:

- **Stage 1** comes from `python run_pipeline.py --stages 1`, with seed 42 and 50 iterations × 24 solutions (1,200 candidate models).
  - The winning configuration was UMAP with 35 neighbors, 8 components, and min_dist 0.05; HDBSCAN with a minimum cluster size of 35; and a maximum of 21 topics.
  - It gave 20 topics at **c_v = 0.790**.
  - Every topic is at least 95.6% pure with respect to the ground-truth theme. All five themes surface:
    - Alcohol Delivery and Isolation Drinking: 3 topics;
    - Sports: 2;
    - Social Media Promotions: 5;
    - Restaurant Support: 1;
    - Gaming: 1.

    The remaining 8 topics are everyday content (recipes and chatter).
  - Files: `stage1_parameters.json`, `stage1_all_iteration_results.json`,
    `stage1_coherence_curve.png`, and `stage1_topics_with_ground_truth.csv`. The last of these
    gives each topic's words, size, and majority ground-truth theme. It is the answer key for a
    Stage 3 synthesis exercise.
- **Stage 5** comes from `python run_pipeline.py --ground-truth --stages 5`.
  - It reproduces the published prevalence table and significance pattern.
  - Files: `stage5_ground_truth_prevalence_by_period.csv`, `stage5_ground_truth_ztest_results.csv`,
    and `stage5_ground_truth_theme_counts.csv`.

Stages 2 and 4 call a language model, so their outputs depend on the model and
the moment. No reference outputs are shipped for them. Run them with your own
key and report the model identifier, as the methods preprint recommends.

## What it is not

- **Not real data.** Every brand, person, handle, app, charity, and post is invented. No text
  comes from the dissertation data or from any real social media account. Any
  resemblance to a real brand is coincidental.
- **Not a substitute for the original analysis.** The corpus is generated from
  templates, so it is cleaner and more regular than real brand feeds. Expect
  sharper topics and higher classifier agreement than on real text.
- **Not evidence.** Results computed on this corpus show how the pipeline behaves.
  They say nothing about alcohol marketing.

## Reproducing the files

```bash
cd dtm_pipeline
python make_demo_data.py        # seeded: rewrites these four files byte for byte
python -m pytest tests -q       # includes a check that the shipped files match the generator
```

## Access to the dissertation data

The source data for the published demonstration are brand tweets recorded by
the Prevention Research Lab Twitter Marketing Study (PRL-TMS), and user-generated
tweets from the Computational Media Lab COVID-19 Twitter Dataset. They contain
account-level information and content governed by the platform's terms of service
and by the agreements under which they were collected, so they are not posted
publicly. They are available from the corresponding author
(jethomasphd@gmail.com) on reasonable request for non-commercial research, under
a data use agreement consistent with those terms.
