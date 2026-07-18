/* demo.js — synthetic demonstration corpus (browser port of
 * make_demo_data.py): 600 documents across five latent themes plus noise,
 * spread over three study periods, with a 250-document human benchmark. */

import { mulberry32, choice } from "./util.js";

export const NONE_LABEL = "The text does not fit into any of these themes";

const THEMES = {
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
  [NONE_LABEL]: [
    "happy holidays from all of us to all of you",
    "what a beautiful sunset over the distillery today",
    "our founder started this company with a simple dream",
    "quality craftsmanship in every single bottle we make",
  ],
};

const PERIODS = [
  ["2019-03-01", "2019-12-15"],
  ["2020-03-15", "2020-05-25"],
  ["2020-08-01", "2021-06-15"],
];

const EXTRAS = ["", " cheers", " tonight", " this weekend", " friends",
  " lets go", " dont miss it", " see you there"];

export function makeDemoData(seed = 7) {
  const rng = mulberry32(seed);
  const rows = [];
  for (const [theme, templates] of Object.entries(THEMES)) {
    for (let i = 0; i < 100; i++) {
      const [start, end] = choice(PERIODS, rng);
      const t0 = Date.parse(start), t1 = Date.parse(end);
      const date = new Date(t0 + (t1 - t0) * rng()).toISOString().slice(0, 10);
      rows.push({ tweet: choice(templates, rng) + choice(EXTRAS, rng), date, _true_theme: theme });
    }
  }
  for (let i = rows.length - 1; i > 0; i--) { // seeded shuffle
    const j = Math.floor(rng() * (i + 1));
    [rows[i], rows[j]] = [rows[j], rows[i]];
  }
  const corpus = rows.map(({ tweet, date }) => ({ tweet, date }));
  const benchmark = rows.slice(0, 250).map(r => ({ tweet: r.tweet, human_label: r._true_theme }));
  return { corpus, benchmark };
}

/** The demonstration study's theme list (from the paper). */
export const DEMO_THEMES = Object.keys(THEMES).filter(t => t !== NONE_LABEL);
