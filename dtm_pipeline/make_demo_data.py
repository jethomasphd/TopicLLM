"""
make_demo_data.py — Generate a synthetic corpus + human benchmark so the
pipeline can be smoke-tested end-to-end without the PRL-TMS dataset.

Creates:
    tweet_data.csv   (tweet, date) — 600 synthetic documents across 5 latent
                     themes + noise, spread over the three study periods
    human_labels.csv (tweet, human_label) — 250-document benchmark
"""

import random

import pandas as pd

random.seed(7)

THEMES = {
    "Alcohol Delivery and Isolation Drinking": [
        "get your favorite drinks delivered to your door in under an hour",
        "staying in tonight order delivery and enjoy a cold one at home",
        "home bar restocked with contactless delivery use code stayhome",
        "sip from the couch delivery is on us this weekend",
    ],
    "Restaurant Support": [
        "support your local restaurant workers order takeout tonight",
        "we are donating to the restaurant relief fund join us",
        "bars and restaurants need us tag your favorite spot to support",
        "every order helps a restaurant worker get back on their feet",
    ],
    "Social Media Promotions": [
        "retweet and follow for a chance to win fresh merch for your crew",
        "going live on instagram tonight tune in for the virtual tour",
        "tag a friend and tell us your favorite for a chance to win",
        "new merch collection drops this week follow to win",
    ],
    "Sports": [
        "join our virtual draft party tonight with celebrity hosts",
        "show us your home putting challenge for a chance at the trophy",
        "game day at home submit your team spirit video",
        "the league is back tune in and grab a cold one",
    ],
    "Gaming": [
        "charity royale on twitch tonight pro athletes raise money for local causes",
        "live right now on twitch come watch the final round",
        "gaming for good join the stream and donate tonight",
        "the tournament finale streams tonight on twitch tv",
    ],
    None: [  # noise: no theme
        "happy holidays from all of us to all of you",
        "what a beautiful sunset over the distillery today",
        "our founder started this company with a simple dream",
        "quality craftsmanship in every single bottle we make",
    ],
}

PERIODS = [("2019-03-01", "2019-12-15"), ("2020-03-15", "2020-05-25"),
           ("2020-08-01", "2021-06-15")]


def jitter(text: str) -> str:
    """Cheap lexical variation so documents aren't literal duplicates."""
    extras = ["", " cheers", " tonight", " this weekend", " friends",
              " lets go", " dont miss it", " see you there"]
    return text + random.choice(extras)


rows, bench = [], []
for theme, templates in THEMES.items():
    for _ in range(100):
        start, end = random.choice(PERIODS)
        date = pd.Timestamp(start) + (pd.Timestamp(end) - pd.Timestamp(start)) * random.random()
        rows.append({"tweet": jitter(random.choice(templates)),
                     "date": date.date().isoformat(),
                     "_true_theme": theme or "The text does not fit into any of these themes"})

random.shuffle(rows)
df = pd.DataFrame(rows)
df[["tweet", "date"]].to_csv("tweet_data.csv", index=False)
df.iloc[:250][["tweet"]].assign(human_label=df.iloc[:250]["_true_theme"]).to_csv(
    "human_labels.csv", index=False)
print(f"Wrote tweet_data.csv ({len(df)} docs) and human_labels.csv (250 benchmark docs).")
