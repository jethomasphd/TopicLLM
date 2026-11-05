"""
make_demo_data.py — Build the TopicLLM demonstration corpus.

A fully synthetic, openly licensed (CC BY 4.0) stand-in for the restricted
dissertation data. It lets anyone run all five stages end to end, and its
design mirrors the published demonstration (Thomas, 2025, Study 1):

  * 5,872 posts by 11 brands, Jan 2019 - Jul 2021, with the same per-brand
    volumes and the same period sizes as the dissertation corpus
    (pre-pandemic 1,707; February 2020 253; peri-pandemic 806; post 3,106);
  * five latent themes plus "no theme", carried by the same kinds of
    campaigns the dissertation reports (delivery and stay-home drinking,
    restaurant relief, live streams and giveaways, a virtual draft party and
    home sports challenges, a charity gaming tournament) among everyday brand
    chatter (recipes, holidays, launches, heritage, events, ...);
  * per-period theme counts calibrated so that, with ground-truth labels,
    Stage 5 returns the dissertation's published prevalence table and
    z statistics. A classifier's output approaches that table to the extent
    that it agrees with the ground truth;
  * a 250-post human-labeled benchmark drawn from the lockdown months.

Everything is fictional: brands, people, handles, apps, charities and posts.
No text is taken from the dissertation data or from any real social media
account. Running this script reproduces the files byte for byte (seeded).

Outputs (default: ../docs/data/, served by the website):
    demonstration_corpus.csv        post_id, brand, date, tweet
    demonstration_benchmark.csv     post_id, tweet, human_label
    demonstration_ground_truth.csv  post_id, period, theme, campaign
    demonstration_stopwords.txt     domain stopwords (brand terms + time words)
"""

from __future__ import annotations

import argparse
import calendar
import os
import random
import re
from collections import Counter

import pandas as pd

SEED = 20251
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "..", "docs", "data")

NONE = "The text does not fit into any of these themes"
DEL, RES, SOC, SPO, GAM = ("Alcohol Delivery and Isolation Drinking", "Restaurant Support",
                           "Social Media Promotions", "Sports", "Gaming")
THEMES = [DEL, RES, SOC, SPO, GAM]

# --------------------------------------------------------------------------- #
# Design targets (aggregates published in the dissertation)
# --------------------------------------------------------------------------- #

PERIODS = {  # name: (first month, last month), inclusive
    "pre": ((2019, 1), (2020, 1)),
    "feb2020": ((2020, 2), (2020, 2)),
    "peri": ((2020, 3), (2020, 5)),
    "post": ((2020, 6), (2021, 7)),
}
PERIOD_N = {"pre": 1707, "feb2020": 253, "peri": 806, "post": 3106}

# Theme counts per period. With ground-truth labels these reproduce the
# published prevalence table (Table 2) and its z statistics; February 2020
# sits between periods and follows the pre-pandemic rates.
THEME_COUNTS = {
    "pre":     {DEL: 155, RES: 32, SOC: 113, SPO: 140, GAM: 19},
    "feb2020": {DEL: 23,  RES: 5,  SOC: 17,  SPO: 21,  GAM: 3},
    "peri":    {DEL: 140, RES: 44, SOC: 133, SPO: 92,  GAM: 16},
    "post":    {DEL: 369, RES: 52, SOC: 330, SPO: 277, GAM: 50},
}

# Relative monthly posting volume (shape of the dissertation's Figure 1).
MONTH_WEIGHTS = {
    (2019, 1): 78, (2019, 2): 123, (2019, 3): 97, (2019, 4): 177, (2019, 5): 124,
    (2019, 6): 100, (2019, 7): 129, (2019, 8): 115, (2019, 9): 110, (2019, 10): 150,
    (2019, 11): 185, (2019, 12): 161, (2020, 1): 253, (2020, 2): 280, (2020, 3): 160,
    (2020, 4): 326, (2020, 5): 367, (2020, 6): 146, (2020, 7): 236, (2020, 8): 271,
    (2020, 9): 263, (2020, 10): 270, (2020, 11): 201, (2020, 12): 256, (2021, 1): 178,
    (2021, 2): 281, (2021, 3): 246, (2021, 4): 220, (2021, 5): 197, (2021, 6): 213,
    (2021, 7): 226,
}

# Eleven fictional brands with the dissertation's per-brand volumes.
BRANDS = {
    "Lanternlight Lager":        dict(n=1142, handle="LanternlightBeer", kind="lager"),
    "Coral Cove Rum":            dict(n=755,  handle="CoralCoveRum", kind="rum"),
    "Brightwater Hard Seltzer":  dict(n=695,  handle="BrightwaterSeltzer", kind="seltzer"),
    "Old Ferry Brewing":         dict(n=653,  handle="OldFerryBrewing", kind="craft"),
    "Kingsgate Brewery":         dict(n=594,  handle="KingsgateBrew", kind="craft"),
    "Hollowmere Herbal Liqueur": dict(n=592,  handle="Hollowmere", kind="liqueur"),
    "Copper Hollow Whiskey":     dict(n=535,  handle="CopperHollow", kind="whiskey"),
    "Prairie Crown Lager":       dict(n=409,  handle="PrairieCrown", kind="lager"),
    "Mareta Rum":                dict(n=233,  handle="MaretaRum", kind="rum"),
    "Frostline Vodka":           dict(n=147,  handle="FrostlineVodka", kind="vodka"),
    "Tidepool Hard Seltzer":     dict(n=117,  handle="TidepoolSeltzer", kind="seltzer"),
}

# Short product nicknames used in copy.
SHORT = {
    "Lanternlight Lager": ["Lanternlight", "a Lanternlight", "an ice-cold Lanternlight"],
    "Coral Cove Rum": ["Coral Cove", "Coral Cove Rum", "a Coral Cove and pineapple"],
    "Brightwater Hard Seltzer": ["Brightwater", "a Brightwater", "a can of Brightwater"],
    "Old Ferry Brewing": ["Old Ferry", "an Old Ferry lager", "an Old Ferry IPA"],
    "Kingsgate Brewery": ["Kingsgate", "a Kingsgate pale ale", "a Kingsgate pint"],
    "Hollowmere Herbal Liqueur": ["Hollowmere", "a Hollowmere shot", "a Hollowmere tonic"],
    "Copper Hollow Whiskey": ["Copper Hollow", "a Copper Hollow neat", "a Copper Hollow old fashioned"],
    "Prairie Crown Lager": ["Prairie Crown", "a Prairie Crown", "a cold Prairie Crown"],
    "Mareta Rum": ["Mareta", "a Mareta mojito", "Mareta Rum"],
    "Frostline Vodka": ["Frostline", "a Frostline martini", "a Frostline soda"],
    "Tidepool Hard Seltzer": ["Tidepool", "a Tidepool", "a can of Tidepool"],
}

FIRST = ["Maya", "Jordan", "Theo", "Priya", "Marcus", "Elena", "Darius", "Sofia", "Caleb",
         "Nina", "Owen", "Rosa", "Isaiah", "Lena", "Mateo", "Avery", "Grant", "Imani"]
LAST = ["Reyes", "Brooks", "Okafor", "Lindqvist", "Hale", "Moreno", "Castellano", "Whitfield",
        "Nakamura", "Duval", "Pryce", "Ashby", "Kowalski", "Fontaine", "Mercer", "Oyelaran"]
CITIES = ["Austin", "Denver", "Chicago", "Nashville", "Portland", "Atlanta", "Phoenix", "Boston",
          "San Diego", "Detroit", "Kansas City", "Charlotte", "Milwaukee", "Tampa", "Omaha"]
TIMES = ["7pm ET", "8pm ET", "9pm ET", "6pm PT", "8pm CT", "7pm CT", "9pm EST", "6pm EST"]
DAYS = ["tonight", "this Friday", "Saturday night", "tomorrow night", "this weekend", "Thursday"]
CODES = ["STAYIN5", "COVE5", "CHEERS5", "SIPHOME", "POURLY5", "HOMEBAR", "FIRSTROUND", "BRIGHT5"]

# --------------------------------------------------------------------------- #
# Campaign copy. Each campaign composes posts from openers x bodies x closers
# with slot filling, so no two posts need be identical.
# --------------------------------------------------------------------------- #

CAMPAIGNS = {
    # ---------------- Alcohol Delivery and Isolation Drinking ---------------
    "delivery_app": dict(theme=DEL, brands=None, open=[
        "Your couch, your rules.", "Skip the store.", "Happy hour, delivered.",
        "No pants required.", "Restock without leaving the house.", "Running low?",
        "The fridge called. It's empty.", "Doorstep delivery is the new last call.",
    ], body=[
        "Get {short} delivered to your door in 60 minutes or less with Pourly.",
        "Order {short} on Pourly and get $5 off your first delivery with code {code}.",
        "{brand} is now available for same-day delivery in {city} through Pourly.",
        "Have {short} delivered straight to your door. Use code {code} for $5 off your first order.",
        "Delivery is on us this weekend: order {short} through Pourly with code {code}.",
        "Tap, order, sip. {brand} delivered in under an hour on Pourly.",
        "Free delivery on your first Pourly order of {short}. Code {code}.",
        "Contactless delivery of {short}, from our shelf to your doorstep.",
    ], close=["", "", "Order now, link in bio.", "Must be 21+ to order.", "#DeliveredDaily",
              "Cheers from a safe distance.", "#DoorstepDrinks"]),

    "shop_online": dict(theme=DEL, brands=None, open=[
        "Gift giving made easy.", "Last-minute gift? Covered.", "Shopping for the bottle lover in your life?",
        "Can't make it to the store?", "Stock the bar before the big game.",
    ], body=[
        "Order {short} online and have it shipped to their door.",
        "Order {short} online for curbside pickup at your local store.",
        "Ship a bottle of {brand} anywhere it's legal, ordered online in minutes.",
        "{brand} gift packs ship to your door. Order online today.",
        "Order online and get {short} delivered before the weekend.",
        "Our online shop now delivers {short} in {city}.",
    ], close=["", "Link in bio.", "Free shipping this week.", "Must be 21+ to order.", "#ShopOnline"]),

    "stay_home_sips": dict(theme=DEL, brands=None, open=[
        "Pro tip:", "WFH hack:", "Day 23 of staying home.", "Quarantine life:", "Hot take:",
        "Staying in, again.", "Isolation update:", "New office, same deadlines.",
    ], body=[
        "pour {short} into a coffee mug and nobody on the video call will know.",
        "the commute is now from the couch to the fridge for {short}.",
        "virtual happy hour starts at 5, and {short} is already on my desk.",
        "{short} pairs perfectly with a blanket, a movie and nowhere to be.",
        "the home bar is open, the dress code is pajamas, and {short} is pouring.",
        "make it a quarantini night with {short} and whatever is left in the fridge.",
        "drinking at home hits different when {short} is cold and the couch is warm.",
        "your living room is the best bar in town tonight. Stay home with {short}.",
        "staying home is easier with {short} and a video call with the crew.",
    ], close=["", "#StayHomeSips", "#HomeBarHours", "#VirtualHappyHour", "Stay home, stay safe.",
              "Who else is drinking from a mug today?"]),

    "little_sunshine": dict(theme=DEL, brands={"Coral Cove Rum": 0.8, "Mareta Rum": 0.2}, open=[
        "Need a little sunshine?", "Brighter days are on the way.", "Sending a bit of sunshine your way.",
        "Bring the beach inside.", "Island time, living room edition.",
    ], body=[
        "Order {short} for delivery and add a bit of sunshine to your day. #ALittleSunshine",
        "Share a bit of sunshine: tell us the happiest part of your day. #ALittleSunshine",
        "Get {short} delivered and make today a little sunnier. Code {code} for $5 off.",
        "A bit of sunshine, delivered to your door in under an hour. #ALittleSunshine",
        "Happy hour at home just got sunnier. Order {short} and share your view. #ALittleSunshine",
        "Your daily dose of sunshine: {short}, ice, and a beach playlist. #ALittleSunshine",
    ], close=["", "Order through Pourly.", "Stay sunny.", "#StaySunny"]),

    # ----------------------------- Restaurant Support -----------------------
    "serve_strong_fund": dict(theme=RES, brands={"Old Ferry Brewing": 0.6, "Kingsgate Brewery": 0.2,
                                                 "Lanternlight Lager": 0.2}, open=[
        "Restaurant and bar workers need us.", "Update on the #ServeThemStrong fund:",
        "The people who serve us every day are hurting.", "Thank you for your generosity.",
        "Restaurants are the heart of our neighborhoods.",
    ], body=[
        "Every donation to the #ServeThemStrong relief fund goes straight to out-of-work restaurant workers.",
        "The #ServeThemStrong fund has mailed 400 $1,000 grants to restaurant and bar workers, with more going out today.",
        "We're matching every donation to the #ServeThemStrong fund to help restaurant workers through COVID closures.",
        "Brewers across the country have joined the #ServeThemStrong fund to support restaurant workers. Donate today.",
        "Donate to the #ServeThemStrong relief fund and help restaurant workers pay rent this month.",
        "Our #ServeThemStrong beer sends every dollar of profit to the restaurant worker relief fund.",
        "Help restaurant workers hit hardest by COVID: donate to the #ServeThemStrong fund.",
    ], close=["", "Donate at the link in bio.", "Thank you for helping restaurant workers.", "#SupportRestaurants"]),

    "takeout_support": dict(theme=RES, brands=None, open=[
        "We miss bars too.", "Your local restaurant needs you.", "Order takeout tonight.",
        "Calling all restaurants:", "Support local restaurants.",
    ], body=[
        "Order takeout from your favorite restaurant and we'll donate to the restaurant worker relief fund.",
        "Restaurants and bars: tell us you're open for takeout and we'll help support your workers.",
        "Tag a local restaurant still serving curbside and we'll donate $5 to help its workers.",
        "Order takeout tonight and tip big: restaurant workers need our support right now.",
        "Every takeout order helps a restaurant keep its workers employed. Support local restaurants tonight.",
        "Help keep your neighborhood restaurant open: order takeout and support the workers behind it.",
    ], close=["", "#OpenForTakeout", "#SupportRestaurants", "#TipYourServer"]),

    "bar_partners": dict(theme=RES, brands=None, open=[
        "Supporting restaurant workers.", "Restaurant spotlight:", "Meet the team behind your pint.",
        "Our favorite local restaurant:", "Behind every great pour is a great bartender.",
    ], body=[
        "This month a portion of every pint sold at {city} restaurants goes to the restaurant workers' fund.",
        "We're proud to support the restaurant workers and bartenders who keep {city} running. Donate to their fund.",
        "Visit our partner restaurants in {city} this week; a dollar from every {short} supports their workers.",
        "Our hospitality fund helps {city} restaurant workers with emergency grants. Donate or apply today.",
        "We donated $50,000 to the {city} restaurant workers' fund to help bartenders and servers.",
    ], close=["", "#SupportRestaurants", "#HospitalityHeroes", "Tip your bartender."]),

    # -------------------------- Social Media Promotions ---------------------
    "living_room_tour": dict(theme=SOC, brands={"Lanternlight Lager": 0.5, "Hollowmere Herbal Liqueur": 0.25,
                                                "Kingsgate Brewery": 0.25}, open=[
        "Going live now!", "Tune in tonight.", "We're live in five.", "Don't miss it.",
        "Your living room, our stage.",
    ], body=[
        "Join the #LivingRoomTour on Instagram Live {day} at {time} with a set from {person}.",
        "{person} is going live on our Instagram at {time} for the #LivingRoomTour. Grab {short} and tune in.",
        "The #LivingRoomTour: Home Edition streams on Instagram and Facebook Live {day} at {time}.",
        "Live music, virtual bar, real drinks. Tune in to the #LivingRoomTour on IG {day}.",
        "Tonight's #LivingRoomTour stop: {person} live from their kitchen at {time} on Instagram.",
        "We're bringing the dive bar to your living room. #LivingRoomTour live on IG at {time}.",
    ], close=["", "Link in bio.", "Set your reminder.", "See you there."]),

    "howdy_neighbor": dict(theme=SOC, brands={"Prairie Crown Lager": 0.55, "Brightwater Hard Seltzer": 0.25,
                                              "Tidepool Hard Seltzer": 0.2}, open=[
        "Who would you share one with right now?", "Giveaway time!", "Win it before it's gone.",
        "New merch alert.", "Tag your crew.",
    ], body=[
        "Tag a friend you miss and say #HowdyNeighbor for a chance to win our new crewneck.",
        "Retweet and follow for a chance to win fresh #HowdyNeighbor merch for your whole crew.",
        "Reply with the friend you'd share {short} with and you could win a year of merch.",
        "Our new merch collection drops this week. Follow and retweet for a chance to win it first.",
        "Say #HowdyNeighbor to a friend below. Five winners get a #HowdyNeighbor hoodie.",
        "Show us your best happy hour selfie for a chance to win merch for your video call crew.",
    ], close=["", "Rules in bio. 21+.", "Winners announced Friday.", "Good luck!"]),

    "contests": dict(theme=SOC, brands=None, open=[
        "Contest time!", "Want to win?", "Comment below.", "Giveaway alert.", "Follow us for more.",
        "It's giveaway week.", "Last chance to enter.",
    ], body=[
        "Comment with your favorite {short} memory for a chance to win festival tickets.",
        "Follow us and share this post for a chance to win a {brand} cooler.",
        "Post a photo with {short} using #CheersWithUs and you could win a weekend trip.",
        "Like, follow and tag two friends to enter our summer giveaway.",
        "Tell us your go-to bar order in the replies. Our favorite answer wins a gift pack.",
        "Follow us on Instagram for exclusive giveaways and first looks at new releases.",
        "Retweet this post for a chance to win {brand} glassware for your home bar.",
        "Caption this photo in the replies. The best caption wins a {brand} jacket.",
        "Share your best patio setup with #CheersWithUs for a chance to win a grill.",
        "We're giving away ten {brand} hoodies. Follow and retweet to enter.",
        "Vote for our next limited flavor in the poll and you could win the first case.",
        "Enter our fall sweepstakes for a chance at concert tickets in {city}.",
        "Duet our latest video for a shot at a year of {brand} merch.",
        "Drop a photo of your pet in a {brand} bandana for a chance to win.",
    ], close=["", "Rules in bio. 21+.", "Winners chosen at random.", "#Giveaway", "Good luck!"]),

    # ----------------------------------- Sports -----------------------------
    "draft_night": dict(theme=SPO, brands={"Lanternlight Lager": 0.8, "Brightwater Hard Seltzer": 0.2}, open=[
        "It's draft night!", "Tonight!", "Draft party, living room edition.", "Boo the commissioner from home.",
        "Pick is in.",
    ], body=[
        "Join the #DraftNightIn virtual party on YouTube at {time} hosted by {celeb} and {celeb2}.",
        "{celeb} hosts the #DraftNightIn after-party tonight with special guest {celeb2}. Tune in on YouTube.",
        "Watch the virtual draft with us: #DraftNightIn streams live at {time} with {celeb}.",
        "Boo the commissioner with {celeb} at the #DraftNightIn party, live on YouTube {day}.",
        "Football's draft goes virtual and so does our party. #DraftNightIn with {celeb} at {time}.",
    ], close=["", "Grab {short} and join us.", "#DraftNightIn", "Who's your team taking first?"]),

    "couch_league": dict(theme=SPO, brands={"Lanternlight Lager": 0.45, "Brightwater Hard Seltzer": 0.3,
                                            "Tidepool Hard Seltzer": 0.1, "Prairie Crown Lager": 0.15}, open=[
        "Sports are on hold. Your skills aren't.", "Challenge accepted.", "The #CouchLeague is here.",
        "Think you've got skills?", "Home team, assemble.",
    ], body=[
        "Submit your best at-home trick shot video with #CouchLeague for a chance to win a team prize.",
        "Show us your backyard putting setup. Best #CouchLeague video wins a custom putting mat.",
        "Pro athletes picked their #CouchLeague teams. Submit your home workout video to join one.",
        "Laundry basket hoops, hallway hockey, kitchen soccer: post your #CouchLeague challenge video.",
        "The #CouchLeague challenge: ten books, three notebooks and a foam roller. Stick the landing.",
        "Week two of the #CouchLeague home sports challenge is open. Submit your video by Friday.",
    ], close=["", "Rules in bio. 21+.", "#CouchLeague", "Tag a teammate."]),

    "game_day": dict(theme=SPO, brands=None, open=[
        "Game day!", "Kickoff is almost here.", "It's playoff season.", "Tailgate ready?",
        "What a finish!", "Opening day vibes.", "Big game this weekend.", "Overtime!",
    ], body=[
        "Grab {short} and settle in for the big game.",
        "Proud to be the official beer of the {city} football club this season.",
        "Fire up the grill and grab {short}. Kickoff at {time}.",
        "Brackets are busted and {short} is cold. Who's still alive?",
        "Nothing beats {short} at the ballpark on opening day.",
        "Proud sponsor of the {city} Open golf tournament this weekend.",
        "Win or lose, {short} tastes better with your team.",
        "Watching the game in {city} with {short} in hand.",
        "Our {city} game day crew has the cooler stocked with {short}.",
        "Hockey night in {city}: puck drops at {time}.",
        "Tip-off at {time}. {short} is ready when you are.",
        "Race day in {city}, and the {short} is on ice.",
        "Soccer season opener in {city} {day}. Bring your scarf and your team spirit.",
        "Third quarter, tied game, {short} in hand.",
        "The {city} marathon runs {day}. Cheering on every runner, and saving them {short} for later.",
        "Fantasy draft night with the league: snacks, smack talk and {short}.",
    ], close=["", "", "#GameDay", "#Playoffs", "Who are you rooting for?", "Drink responsibly.", "Go team."]),

    # ----------------------------------- Gaming -----------------------------
    "charity_royale": dict(theme=GAM, brands={"Lanternlight Lager": 0.65, "Brightwater Hard Seltzer": 0.35}, open=[
        "Excited to announce the Charity Royale.", "Live right now on Twitch!", "Finals tonight!",
        "Congrats to the Charity Royale champions!", "Semifinals are set.",
    ], body=[
        "Twenty-four pro athletes battle in the Charity Royale on Twitch to raise money for local causes.",
        "The Charity Royale finals stream tonight at {time} on our Twitch channel. All money goes to charity.",
        "{gamer} and {gamer2} advance to the Charity Royale semifinals. Watch live on Twitch.",
        "Every Charity Royale win sends money to local food banks. Tune in on Twitch at {time}.",
        "Watch {gamer} take on {gamer2} live on Twitch for the Charity Royale title.",
    ], close=["", "#CharityRoyale", "Tune in.", "Gaming for good."]),

    "game_night": dict(theme=GAM, brands=None, open=[
        "Game night.", "Controllers ready?", "Esports fans:", "Stream starts soon.", "GG!",
    ], body=[
        "Proud to sponsor the {city} esports team at this weekend's tournament. Watch on Twitch.",
        "Our gaming stream is live at {time}: {gamer} plays with fans for prizes.",
        "Join our community game night on Twitch {day}. Winners get {brand} gear.",
        "The esports finals are on and {short} is the official drink of the watch party (21+).",
        "New partnership: {brand} is teaming up with {gamer} for a monthly gaming stream.",
    ], close=["", "#GameNight", "Link in bio.", "GG everyone."]),
}

# Period-specific mix of campaigns within each theme.
CAMPAIGN_MIX = {
    DEL: {"pre": {"delivery_app": .5, "shop_online": .5},
          "feb2020": {"delivery_app": .5, "shop_online": .5},
          "peri": {"delivery_app": .3, "stay_home_sips": .4, "little_sunshine": .3},
          "post": {"delivery_app": .35, "stay_home_sips": .25, "little_sunshine": .25, "shop_online": .15}},
    RES: {"pre": {"bar_partners": 1.0}, "feb2020": {"bar_partners": 1.0},
          "peri": {"serve_strong_fund": .55, "takeout_support": .45},
          "post": {"serve_strong_fund": .35, "takeout_support": .35, "bar_partners": .3}},
    SOC: {"pre": {"contests": 1.0}, "feb2020": {"contests": 1.0},
          "peri": {"living_room_tour": .5, "howdy_neighbor": .5},
          "post": {"living_room_tour": .3, "howdy_neighbor": .35, "contests": .35}},
    SPO: {"pre": {"game_day": 1.0}, "feb2020": {"game_day": 1.0},
          "peri": {"draft_night": .8, "couch_league": .2},
          "post": {"couch_league": .25, "game_day": .75}},
    GAM: {"pre": {"game_night": 1.0}, "feb2020": {"game_night": 1.0},
          "peri": {"charity_royale": 1.0},
          "post": {"charity_royale": .4, "game_night": .6}},
}

# --------------------------------------------------------------------------- #
# Everyday brand content ("no theme")
# --------------------------------------------------------------------------- #

COCKTAILS = [
    ("Mule", "2 oz {spirit}, 4 oz ginger beer, half a lime, served over ice in a copper mug"),
    ("Sunrise", "1.5 oz {spirit}, orange juice, a splash of grenadine, poured slowly over ice"),
    ("Spritz", "1 part {spirit}, 2 parts soda water, a squeeze of grapefruit and a sprig of rosemary"),
    ("Sour", "2 oz {spirit}, 3/4 oz lemon juice, 1/2 oz simple syrup, shaken hard with ice"),
    ("Highball", "1.5 oz {spirit} topped with sparkling water and a long lemon twist"),
    ("Punch", "{spirit}, pineapple juice, coconut water and a dash of bitters, batched for a crowd"),
    ("Smash", "2 oz {spirit}, muddled mint, fresh berries and crushed ice"),
    ("Toddy", "1.5 oz {spirit}, hot water, honey, lemon and a cinnamon stick"),
    ("Colada", "2 parts {spirit}, 3 parts pineapple, 1 part coconut cream, blended until smooth"),
    ("Fizz", "1.5 oz {spirit}, lemon, egg white and soda, dry shaken then shaken again"),
]
SPIRIT = {"rum": "rum", "whiskey": "whiskey", "vodka": "vodka", "liqueur": "herbal liqueur",
          "lager": "lager", "craft": "pale ale", "seltzer": "hard seltzer"}

HOLIDAYS = {
    1: ["New year, same great taste. Here's to {year}.", "Resolution: more nights in with good friends.",
        "Cheers to fresh starts and the first {short} of the year."],
    2: ["Roses are red, {short} is cold.", "Galentine's plans: snacks, movies and {short}.",
        "Love is sharing the last {short}."],
    3: ["Wearing green and pouring {short}.", "Spring forward, sip slowly.",
        "The luck of the Irish, and a cold {short}."],
    4: ["April showers bring {short} flowers. Okay, that's not how it works.", "Spring cleaning the bar cart.",
        "Patio season is almost here."],
    5: ["Here's to every mom who deserves a quiet hour and {short}.", "Memorial Day weekend starts now.",
        "May flowers, longer evenings."],
    6: ["First day of summer. Plan accordingly.", "Dads, this one's for you. Happy Father's Day.",
        "Sun's out, cans out."],
    7: ["Fireworks, burgers and {short}. Happy Fourth.", "Peak summer, peak patio.",
        "Red, white and {short}."],
    8: ["Dog days of summer call for {short}.", "Last call for summer vacation.",
        "August heat, cold {short}."],
    9: ["Sweater weather is coming.", "Back-to-school for the kids, back-to-patio for the adults.",
        "Hello, fall. We've been expecting you."],
    10: ["Spooky season pairs well with {short}.", "Costume ideas: a very tall can of {short}.",
         "Pumpkins carved, {short} poured."],
    11: ["Grateful for good friends and {short}.", "Pass the stuffing and the {short}.",
         "Thanksgiving prep: brine the turkey, chill the {short}."],
    12: ["Deck the halls with {short}.", "Holiday party season, sorted.",
         "Wrapping gifts is easier with {short} nearby."],
}

EVERYDAY = {
    "recipe": None,  # generated from COCKTAILS
    "launch": [
        "Meet our newest flavor: {flavor}. Available now wherever {brand} is sold.",
        "Introducing {brand} {flavor}, bright and crisp with a clean finish.",
        "Limited release: {flavor} is back for a few short weeks.",
        "Say hello to the {flavor} variety pack, landing on shelves this month.",
        "Our {flavor} small batch just dropped. Find it near you.",
    ],
    "heritage": [
        "Since {founded}, {brand} has been made the slow way.",
        "Every barrel tells a story. Ours started in {founded}.",
        "Our brewmaster tastes every batch before it leaves the floor.",
        "Small batch, big patience. That's how {brand} has always been made.",
        "Same recipe since {founded}. Some things don't need fixing.",
        "Meet {person}, who has been on our bottling line for twenty years.",
    ],
    "events": [
        "See you at the {city} music festival this weekend. Find us at the main stage bar.",
        "We're pouring at the {city} food and wine festival all weekend.",
        "Live music on the brewery patio {day}, starting at {time}.",
        "Catch {person} live at our {city} taproom {day}.",
        "Our summer concert series kicks off in {city} {day}.",
    ],
    "mood": [
        "Friday feeling: {short} and absolutely no plans.", "Weekend loading.",
        "Some days call for {short}. Today is one of them.", "Cheers to the little wins.",
        "Slow Sunday, cold {short}.", "Sunset, porch, {short}. That's the post.",
        "Long week? We get it.", "Good friends, good stories, {short}.",
    ],
    "responsibility": [
        "Enjoy {short} responsibly. Plan your ride home before the first sip.",
        "Our cans are now made with 70% recycled aluminum.",
        "Proud to support designated driver programs in {city} this holiday season.",
        "We planted 5,000 trees this year with our watershed partners.",
        "Know when to say when. Drink responsibly.",
        "Our brewery now runs on 100% renewable electricity.",
    ],
    "pairing": [
        "{short} with tacos. Trust us.", "Pizza night pairs with {short}.",
        "Grilled shrimp and {short}: the perfect summer plate.",
        "Barbecue season calls for {short} and a big pile of brisket.",
        "{short} and spicy wings: a pairing for the ages.",
    ],
    "outdoors": [
        "Lake days and {short}.", "Pack the cooler, we're going camping.",
        "Beach chair, good book, {short}.", "Trail done, {short} earned.",
        "Find us wherever the water is warm and the {short} is cold.",
    ],
}
EVERYDAY_WEIGHTS = {"chatter": 52, "recipe": 9, "holiday": 13, "launch": 7, "heritage": 5,
                    "events": 4, "mood": 4, "responsibility": 3, "pairing": 2, "outdoors": 1}

# Compositional everyday chatter: independent pools so posts spread across
# the semantic space the way real brand feeds do (most real brand posts
# belong to no theme and to no tight cluster).
CHATTER = {
    "sensory": (
        ["This batch", "Our {flavor}", "The spring release", "Our flagship", "Every bottle of {brand}",
         "The reserve cask", "Today's pour", "Our oldest recipe", "The winter seasonal", "A fresh keg",
         "The small-batch {flavor}", "Our single barrel", "The new vintage", "This year's harvest ale",
         "The anniversary bottling", "Our house blend"],
        ["smells like toasted oak and vanilla", "finishes clean with a hint of citrus",
         "has notes of honey and black pepper", "spent three winters in charred barrels",
         "goes down easy on a warm afternoon", "landed on shelves this morning",
         "is brewed with hops from the Pacific Northwest", "uses water from our own spring",
         "took home a gold medal at the state fair", "pours a deep amber color",
         "is lighter than you'd expect", "tastes like a summer orchard",
         "has a soft, biscuity malt backbone", "brings a little smoke and a lot of caramel",
         "is best served just below room temperature", "sold out at the tasting room in a day"]),
    "occasion": (
        ["Rooftop evenings", "Rainy afternoons", "Road trips", "Backyard birthdays", "Late dinners",
         "Wedding toasts", "Book club nights", "Snow days", "Housewarming parties", "Movie marathons",
         "Fishing weekends", "Porch swings", "Long lunches", "Graduation weekends", "Cabin getaways",
         "Anniversary dinners"],
        ["string lights", "a crackling fire", "good records", "an open window", "a long table",
         "the first warm breeze", "old friends", "a good playlist", "fresh-cut grass",
         "a stack of board books", "the smell of rain", "the last light of the day",
         "a full moon", "a borrowed guitar", "homemade bread", "a well-worn armchair"]),
    "crew": (
        ["Our head brewer", "The cellar team", "Our distillery cat", "The bottling crew",
         "The barrel room", "Our tasting room staff", "The packaging line", "Our master blender",
         "The farm crew", "Our quality lab", "The night shift", "Our founder"],
        ["just tapped a fresh batch", "is counting down to harvest", "turned the barrels this morning",
         "spent the week perfecting a new recipe", "found an old label from 1962",
         "is testing a rye we can't stop talking about", "painted a mural on the loading dock",
         "repaired the copper still by hand", "planted a new row of hops",
         "tasted forty samples before lunch", "rearranged the whole barrel room",
         "brought homemade chili for everyone"]),
    "weather": (
        ["Ninety degrees", "The first frost", "A heat wave", "Clear skies", "Peak fall colors",
         "A long weekend", "A foggy morning", "The first snowfall", "A thunderstorm",
         "Golden hour", "A breezy evening", "Spring rain"],
        ["in {city} calls for {short}", "over {city} means it's time for {short}",
         "and {short} on the porch", "in {city}, and somebody brought {short}",
         "in {city} pairs with {short} and a good book", "plus {short} equals a perfect evening"]),
}

PANDEMIC_EVERYDAY = [  # lockdown-era posts that are not one of the five themes
    "Thank you to every nurse, doctor and grocery worker keeping us going.",
    "Our distillery is now producing hand sanitizer for local hospitals.",
    "Stay safe, wash your hands, and check on your neighbors.",
    "We're donating masks and gloves to first responders in {city}.",
    "To everyone on the front lines: thank you.",
]
# Neutral framing for everyday posts. Deliberately no questions, contests or
# tag-a-friend prompts: human coders read those as Social Media Promotions.
EVERYDAY_LEADS = ["", "", "", "Quick reminder:", "Fun fact:", "Simple pleasures.", "Noted.",
                  "From our {city} taproom:", "Straight from the tasting room.", "On the menu today:",
                  "Small joys.", "Just saying.", "For the record:", "Taste test complete."]
EVERYDAY_TAILS = ["", "", "", "Cheers.", "Enjoy responsibly.", "Cheers from {city}.", "Pour accordingly.",
                  "#{tag}", "#{tag} #Cheers", "Made with care in {city}.", "Sip slow.",
                  "Back soon with more.", "Raise a glass.", "21+ only, please.", "As always, cheers."]

FLAVORS = ["Grapefruit Basil", "Black Cherry", "Mango Chili", "Blood Orange", "Cucumber Lime",
           "Toasted Coconut", "Pineapple Ginger", "Honey Lemon", "Wild Berry", "Peach Tea",
           "Watermelon Mint", "Spiced Pear", "Smoked Maple", "Hazy IPA", "Winter Lager"]
FOUNDED = ["1874", "1902", "1933", "1956", "1888", "2004", "1979", "2011"]
GAMERS = ["Vexa", "NorthByNorth", "SlateRunner", "kilnfire", "Pixel_Ox", "Lunewave", "DeepCutDev"]
CELEBS = ["Coach Marcus Reyes", "Tasha Brooks", "Dante 'Big D' Okafor", "Lena Whitfield",
          "Rico Duval", "Hank Mercer"]


# --------------------------------------------------------------------------- #

def tidy(text: str) -> str:
    """Capitalize each sentence start and collapse spaces."""
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"([.!?]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), text)
    return text[:1].upper() + text[1:]


class Writer:
    def __init__(self, rng: random.Random):
        self.r = rng

    def person(self):
        return f"{self.r.choice(FIRST)} {self.r.choice(LAST)}"

    def fill(self, text: str, brand: str, date: pd.Timestamp) -> str:
        r = self.r
        celeb, celeb2 = r.sample(CELEBS, 2)
        gamer, gamer2 = r.sample(GAMERS, 2)
        return text.format(
            brand=brand, short=r.choice(SHORT[brand]), city=r.choice(CITIES), time=r.choice(TIMES),
            day=r.choice(DAYS), code=r.choice(CODES), person=self.person(), celeb=celeb,
            celeb2=celeb2, gamer=gamer, gamer2=gamer2, flavor=r.choice(FLAVORS),
            founded=r.choice(FOUNDED), year=date.year, spirit=SPIRIT[BRANDS[brand]["kind"]],
            tag=brand.split()[0] + r.choice(["Life", "Moments", "Crew", "Cheers", "Time"]))

    def campaign_post(self, key: str, brand: str, date) -> str:
        c, r = CAMPAIGNS[key], self.r
        parts = []
        if r.random() < 0.7:
            parts.append(r.choice(c["open"]))
        parts.append(r.choice(c["body"]))
        close = r.choice(c["close"])
        if close:
            parts.append(close)
        text = " ".join(parts)
        if r.random() < 0.25:
            text += f" @{BRANDS[brand]['handle']}" if r.random() < 0.3 else ""
        return tidy(self.fill(text, brand, date))

    def everyday_post(self, brand: str, date, period: str) -> tuple[str, str]:
        r = self.r
        if period == "peri" and r.random() < 0.18:
            return tidy(self.fill(r.choice(PANDEMIC_EVERYDAY), brand, date)), "pandemic_everyday"
        kinds, weights = zip(*EVERYDAY_WEIGHTS.items())
        kind = r.choices(kinds, weights)[0]
        if kind == "events" and period == "peri":
            kind = "mood"  # no live events during lockdown
        if kind == "chatter":
            register = r.choice(list(CHATTER))
            a, b = CHATTER[register]
            first, second = r.choice(a), r.choice(b)
            if register == "occasion":
                text = f"{first}, {second} and {{short}}."
            else:
                text = f"{first} {second}."
        elif kind == "recipe":
            name, spec = r.choice(COCKTAILS)
            name = f"{brand.split()[0]} {name}"
            lead = r.choice(["Try the {n}:", "Recipe of the week, the {n}:", "Make the {n} at home:",
                             "Weekend project, the {n}:", "Bartender's pick, the {n}:"]).format(n=name)
            text = f"{lead} {spec}."
        elif kind == "holiday":
            text = r.choice(HOLIDAYS[date.month])
        else:
            text = r.choice(EVERYDAY[kind])
        lead = r.choice(EVERYDAY_LEADS)
        if lead.endswith(":") and ":" in text:
            lead = ""  # avoid "On the menu today: Meet our newest flavor: ..."
        text = " ".join(x for x in (lead, text, r.choice(EVERYDAY_TAILS)) if x)
        return tidy(self.fill(text, brand, date)), kind


def month_range(first, last):
    y, m = first
    while (y, m) <= last:
        yield (y, m)
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def allocate(total: int, weights: dict) -> dict:
    """Largest-remainder allocation of `total` items to keys by weight."""
    s = sum(weights.values())
    raw = {k: total * w / s for k, w in weights.items()}
    out = {k: int(v) for k, v in raw.items()}
    for k in sorted(raw, key=lambda k: raw[k] - out[k], reverse=True)[: total - sum(out.values())]:
        out[k] += 1
    return out


def build(seed: int = SEED) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rng = random.Random(seed)
    w = Writer(rng)

    # 1. Dates: allocate each period's posts to months, then to days.
    slots = []
    for period, (first, last) in PERIODS.items():
        months = list(month_range(first, last))
        per_month = allocate(PERIOD_N[period], {m: MONTH_WEIGHTS[m] for m in months})
        for (y, m), n in per_month.items():
            ndays = calendar.monthrange(y, m)[1]
            for _ in range(n):
                slots.append((period, pd.Timestamp(y, m, rng.randint(1, ndays))))

    # 2. Themes: exact per-period counts, randomly placed within the period.
    rows = []
    for period in PERIODS:
        idx = [i for i, s in enumerate(slots) if s[0] == period]
        rng.shuffle(idx)
        labels = []
        for theme, k in THEME_COUNTS[period].items():
            labels += [theme] * k
        labels += [NONE] * (len(idx) - len(labels))
        for i, theme in zip(idx, labels):
            rows.append({"period": period, "date": slots[i][1], "theme": theme})

    # 3. Campaigns within themes (draft night only in late April 2020).
    for row in rows:
        if row["theme"] == NONE:
            continue
        mix = dict(CAMPAIGN_MIX[row["theme"]][row["period"]])
        if "draft_night" in mix and row["date"].month != 4:
            mix.pop("draft_night")
        keys, weights = zip(*mix.items())
        row["campaign"] = rng.choices(keys, weights)[0]

    # 4. Brands: campaign-specific brands first, then fill quotas.
    quota = {b: v["n"] for b, v in BRANDS.items()}
    for row in sorted(rows, key=lambda r: r["theme"] == NONE):
        if row["theme"] == NONE:
            continue
        pref = CAMPAIGNS[row["campaign"]]["brands"]
        if pref:
            choices = [b for b in pref if quota[b] > 0]
            b = rng.choices(choices, [pref[c] for c in choices])[0]
        else:
            avail = [b for b, q in quota.items() if q > 0]
            b = rng.choices(avail, [quota[a] for a in avail])[0]
        row["brand"] = b
        quota[b] -= 1
    remaining = [b for b, q in quota.items() for _ in range(q)]
    rng.shuffle(remaining)
    for row, b in zip([r for r in rows if r["theme"] == NONE], remaining):
        row["brand"] = b

    # 5. Text. Like the analytic sample (duplicate text removed), every post
    #    is unique: redraw on collision, then add a neutral sign-off.
    seen = set()
    signoffs = [f"#{b.split()[0]}{s}" for b in BRANDS for s in ("", "Life", "Crew", "Moments")]
    for row in rows:
        for attempt in range(40):
            if row["theme"] == NONE:
                text, kind = w.everyday_post(row["brand"], row["date"], row["period"])
            else:
                text, kind = w.campaign_post(row["campaign"], row["brand"], row["date"]), row["campaign"]
            if attempt >= 30:
                text = f"{text} {rng.choice(signoffs)}"
            if text not in seen:
                break
        seen.add(text)
        row["tweet"] = text
        if row["theme"] == NONE:
            row["campaign"] = kind

    df = pd.DataFrame(rows).sort_values(["date", "brand"], kind="stable").reset_index(drop=True)
    df.insert(0, "post_id", [f"P{i + 1:05d}" for i in range(len(df))])
    df["date"] = df["date"].dt.date.astype(str)
    df["period"] = df["period"].replace({"feb2020": "between"})

    corpus = df[["post_id", "brand", "date", "tweet"]]
    truth = df[["post_id", "period", "theme", "campaign"]]
    peri = df[df["period"] == "peri"].sample(250, random_state=seed).sort_values("post_id")
    bench = peri[["post_id", "tweet"]].assign(human_label=peri["theme"].values)
    return corpus, bench, truth


def main() -> None:
    ap = argparse.ArgumentParser(description="Build the TopicLLM demonstration corpus.")
    ap.add_argument("--out-dir", default=OUT_DIR)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    corpus, bench, truth = build()
    corpus.to_csv(os.path.join(args.out_dir, "demonstration_corpus.csv"), index=False)
    bench.to_csv(os.path.join(args.out_dir, "demonstration_benchmark.csv"), index=False)
    truth.to_csv(os.path.join(args.out_dir, "demonstration_ground_truth.csv"), index=False)
    stop = ([h.lower() for h in (v["handle"] for v in BRANDS.values())]
            + sorted({w.lower() for b in BRANDS for w in b.split()
                      if w.lower() not in {"hard", "rum", "lager", "brewing", "brewery", "whiskey",
                                           "vodka", "seltzer", "herbal", "liqueur"}})
            + ["am", "pm", "et", "pt", "ct", "est"]
            + [d.lower() for d in calendar.day_name] + [m.lower() for m in calendar.month_name if m])
    with open(os.path.join(args.out_dir, "demonstration_stopwords.txt"), "w") as f:
        f.write(",".join(dict.fromkeys(stop)))

    n_unique = corpus["tweet"].nunique()
    print(f"Wrote {len(corpus):,} posts ({n_unique:,} unique) from {corpus['brand'].nunique()} "
          f"fictional brands, a {len(bench)}-post benchmark, and ground truth to {args.out_dir}/")
    print(truth.groupby("period")["theme"].value_counts().unstack(fill_value=0).to_string())


if __name__ == "__main__":
    main()
