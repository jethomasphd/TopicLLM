"""Build the tutorial's data file and its generated table from public evidence.

    python scripts/build-tutorial.py

Writes:
  docs/data/trump/tutorial.json   compact data for the tutorial's live lab
  docs/tutorial/index.html        fills the <!--t:topics--> table (idempotent)

Inputs are the recorded, public tutorial artifacts only. Standard library.
"""
from __future__ import annotations

import csv
import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRUMP = ROOT / "docs" / "data" / "trump"
CAMPAIGN = TRUMP / "campaign"
PAGE = ROOT / "docs" / "tutorial" / "index.html"
RESIDUAL = "The text does not fit into any of these themes"


def main() -> None:
    run = json.loads((TRUMP / "reference-run.json").read_text(encoding="utf-8"))
    codebook = json.loads((CAMPAIGN / "codebook.json").read_text(encoding="utf-8"))
    short = json.loads((CAMPAIGN / "theme_short_names.json").read_text(encoding="utf-8"))
    prevalence = json.loads((CAMPAIGN / "human_sample_prevalence.json").read_text(encoding="utf-8"))
    with (CAMPAIGN / "theme_map.csv").open(encoding="utf-8", newline="") as handle:
        theme_map = {row["topic"]: row for row in csv.DictReader(handle)}

    topics = []
    for t in run["topics"]:
        mapped = theme_map[str(t["id"])]
        theme = mapped["theme"]
        topics.append({
            "id": t["id"], "words": t["words"], "posts": t["count"],
            "examples": [{"date": e["date"], "text": e["tweet"]} for e in t["examples"][:5]],
            "model_name": t["naming"]["modal_label"], "model_votes": t["naming"]["votes_for_modal"],
            "model_total": t["naming"]["total_votes"], "distinct_names": t["naming"]["distinct_labels"],
            "theme": theme, "short": short[theme],
        })

    themes = list(codebook["themes"])
    data = {
        "schema_version": 1,
        "about": "Tutorial data for the TopicLLM website, built from recorded public evidence by scripts/build-tutorial.py.",
        "topics": topics,
        "themes": themes,
        "residual": RESIDUAL,
        "short_names": short,
        "codebook": codebook,
        "yardstick": {
            "human_agreement": prevalence["human_coder_agreement"],
            "classifier_agreement": prevalence["classifier_agreement"],
            "sample": 250,
        },
    }
    (TRUMP / "tutorial.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")

    rows = []
    for t in topics:
        definition = codebook["themes"][t["theme"]].strip()
        rows.append(
            "<tr>"
            f'<td><details><summary>{escape(t["theme"])}</summary><div class="def">{escape(definition)}</div></details>'
            f'<span class="kw">{escape(", ".join(t["words"][:6]))}</span></td>'
            f'<td class="hide-sm">{escape(t["model_name"])}</td>'
            f'<td class="n">{t["posts"]:,}</td>'
            "</tr>")
    table = ('<table class="topics"><caption class="small" style="text-align:left;caption-side:bottom;padding-top:10px">'
             'Open a theme to read its frozen definition, exactly as the researchers wrote it.</caption>'
             '<thead><tr><th>Theme the researchers kept · cluster words</th><th class="hide-sm">Model\'s proposal</th>'
             '<th class="n">Campaign posts</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table>")
    page = PAGE.read_text(encoding="utf-8")
    import re
    page = re.sub(r"<!--t:topics-->.*?<!--/t:topics-->|<!--t:topics-->",
                  lambda _: f"<!--t:topics-->{table}<!--/t:topics-->", page, count=1, flags=re.S)
    PAGE.write_text(page, encoding="utf-8", newline="\n")
    print(f"wrote docs/data/trump/tutorial.json ({len(topics)} topics) and the tutorial topics table")


if __name__ == "__main__":
    main()
