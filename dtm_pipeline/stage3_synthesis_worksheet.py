"""
stage3_synthesis_worksheet.py — Human-in-the-loop theme synthesis (Stage 3).

Stage 3 is deliberately NOT automated: themes emerge through human
interpretation under the two-researcher consensus protocol (Theme and Topic
system). What software can do is assemble the complete review packet each
researcher needs, and record the consensus in a machine-readable form that
Stage 4 consumes.

Inputs   : stage1/best_model/classified_tweets.csv, stage2/topic_names.csv
Artifacts: pipeline_output/stage3/
             synthesis_worksheet.md   (review packet: per topic — modal label,
                                       vote share, representative words, and a
                                       random sample of mapped documents)
             theme_map_TEMPLATE.csv   (topic -> theme; researchers fill this in)

After the two researchers reach consensus, save the completed template as
pipeline_output/stage3/theme_map.csv and update `themes` in config.py to the
agreed theme names before running Stage 4.
"""

import os

import pandas as pd

from config import CONFIG

SAMPLE_PER_TOPIC = 15  # documents sampled per topic for the review packet


def run_stage3(cfg=CONFIG) -> str:
    """Build the review worksheet and the topic->theme mapping template."""
    s1 = os.path.join(cfg.output_dir, "stage1", "best_model")
    s2 = os.path.join(cfg.output_dir, "stage2")
    out = os.path.join(cfg.output_dir, "stage3")
    os.makedirs(out, exist_ok=True)

    tweets = pd.read_csv(os.path.join(s1, "classified_tweets.csv"))
    names = pd.read_csv(os.path.join(s2, "topic_names.csv"))

    lines = [
        "# Stage 3 Review Packet — Theme Synthesis Worksheet",
        "",
        "Protocol (two-researcher consensus, Theme and Topic system):",
        "1. PRIMARY researcher: for each topic, read the sampled documents,",
        "   confirm the modal LLM label is relevant to the sample, and note",
        "   overlapping thematic connections between topics — reading against",
        "   the current literature of the target domain.",
        "2. Group topics by conceptual similarity into candidate themes.",
        "3. SENIOR researcher: independently review and critique; reach",
        "   consensus through discussion.",
        "4. Record the consensus in theme_map_TEMPLATE.csv (save as",
        "   theme_map.csv) and set `themes` in config.py accordingly.",
        "",
        "A fragmented vote (low modal share) flags a semantically ambiguous",
        "topic — give it extra scrutiny here.",
        "",
    ]

    for _, r in names.sort_values("topic").iterrows():
        t = r["topic"]
        sample = tweets.loc[tweets["topic"] == t, "tweet"]
        sample = sample.sample(min(SAMPLE_PER_TOPIC, len(sample)), random_state=cfg.random_seed)
        lines += [
            f"## Topic {t}: {r['modal_label']}",
            f"- Modal vote share: {r['modal_share']:.1%} "
            f"({r['votes_for_modal']}/{r['total_votes']}); "
            f"margin over runner-up: {r['margin_over_runner_up']:.1%}",
            f"- Representative words: {r['words']}",
            f"- Sampled documents (n={len(sample)}):",
        ]
        lines += [f"    - {txt}" for txt in sample.tolist()]
        lines += ["", "**Primary researcher notes:** ",
                  "**Senior researcher critique:** ",
                  "**Consensus candidate theme:** ", ""]

    with open(os.path.join(out, "synthesis_worksheet.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    template = names[["topic", "modal_label"]].copy()
    template["theme"] = ""  # researchers fill in after consensus
    template.to_csv(os.path.join(out, "theme_map_TEMPLATE.csv"), index=False)

    print(f"[stage3] Review packet written: {out}/synthesis_worksheet.md")
    print(f"[stage3] Fill in {out}/theme_map_TEMPLATE.csv -> save as theme_map.csv,")
    print( "[stage3] then set `themes` in config.py to the consensus names.")
    return out


if __name__ == "__main__":
    run_stage3()
