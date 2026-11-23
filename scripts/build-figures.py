"""Draw the tutorial's figures once, for the website, the paper and the README.

    python scripts/build-figures.py

Reads only public aggregate evidence in docs/data/trump/campaign/ and writes
standalone SVG files to docs/assets/figures/. Each SVG carries its own light
and dark palette (prefers-color-scheme), so the same file works on the site,
on GitHub and inside the PDF (where the light palette is used).

Standard library only.
"""
from __future__ import annotations

import csv
import json
import math
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data" / "trump" / "campaign"
OUT = ROOT / "docs" / "assets" / "figures"
RESIDUAL = "The text does not fit into any of these themes"

# Short display names, shared with the website's JavaScript.
SHORT = json.loads((DATA / "theme_short_names.json").read_text(encoding="utf-8"))

# Light palette as presentation attributes (used by PDF renderers); dark palette
# overrides through CSS when the viewer prefers dark mode.
LIGHT = {"ink": "#0f2436", "ink2": "#3b4f60", "muted": "#6b7c89", "rule": "#e3e8ec",
         "accent": "#0f8a6c", "accentsoft": "#d5eee5", "grey": "#9aa8b2", "greysoft": "#e9edf0",
         "amber": "#b45309", "ambersoft": "#fbecd9", "bg": "#ffffff"}
DARK = {"ink": "#ebf2f4", "ink2": "#c3d2da", "muted": "#93a7b2", "rule": "#26363f",
        "accent": "#5fd3ad", "accentsoft": "#173d33", "grey": "#6f828d", "greysoft": "#1d2b33",
        "amber": "#f0a14a", "ambersoft": "#3a2a14", "bg": "#0d171e"}
FONT = "'IBM Plex Sans', 'Helvetica Neue', Arial, sans-serif"


def style_block() -> str:
    """CSS classes for each colour role; light first, dark under a media query."""
    def rules(p: dict[str, str]) -> str:
        out = []
        for role, colour in p.items():
            out.append(f".f-{role}{{fill:{colour}}}.s-{role}{{stroke:{colour}}}")
        return "".join(out)
    return f"<style>{rules(LIGHT)}@media (prefers-color-scheme: dark){{{rules(DARK)}}}text{{font-family:{FONT}}}</style>"


def svg(width: int, height: int, body: list[str], title: str, desc: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
            f'role="img" aria-labelledby="t d" font-family="{escape(FONT)}">'
            f'<title id="t">{escape(title)}</title><desc id="d">{escape(desc)}</desc>{style_block()}'
            + "".join(body) + "</svg>\n")


def text(x: float, y: float, s: str, role: str = "ink", size: int = 14, anchor: str = "start",
         weight: int = 400, extra: str = "") -> str:
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" '
            f'fill="{LIGHT[role]}" class="f-{role}" {extra}>{escape(s)}</text>')


def rect(x, y, w, h, role, rx=0, stroke: str | None = None) -> str:
    s = f' stroke="{LIGHT[stroke]}" class="f-{role} s-{stroke}" stroke-width="1.5"' if stroke else f' class="f-{role}"'
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(0, w):.1f}" height="{h:.1f}" rx="{rx}" fill="{LIGHT[role]}"{s}/>'


def line(x1, y1, x2, y2, role="rule", width=1.0, dash: str | None = None) -> str:
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{LIGHT[role]}" '
            f'class="s-{role}" stroke-width="{width}"{d}/>')


def circle(cx, cy, r, role, stroke: str | None = None, sw=1.5) -> str:
    if stroke:
        return (f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="none" stroke="{LIGHT[stroke]}" '
                f'class="s-{stroke}" stroke-width="{sw}"/>')
    return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{LIGHT[role]}" class="f-{role}"/>'


def pct(x: float, digits: int | None = None) -> str:
    """Whole percents, with one decimal below 2% so small themes stay distinguishable."""
    if digits is None:
        digits = 1 if 0 < x and round(x * 100) < 2 else 0
    return f"{x * 100:.{digits}f}%"


# ---------------------------------------------------------------- figures ---

def fig_pipeline() -> str:
    """Five stages; the two stages where people decide are marked in amber."""
    W, H = 960, 196
    stages = [("Discover", "A topic model groups", "similar posts", True),
              ("Name", "An LLM proposes a name", "500 times per topic", False),
              ("Define", "Two people write", "the codebook", True),
              ("Check", "Classifier vs. two", "human coders", True),
              ("Report", "Theme shares with", "their uncertainty", False)]
    body, bw, gap, top = [], 168, 30, 38
    for i, (name, l1, l2, human) in enumerate(stages):
        x = i * (bw + gap) + 2
        body.append(rect(x, top, bw, 112, "bg", rx=10, stroke="amber" if human else "rule"))
        body.append(text(x + 18, top + 32, f"0{i + 1}", "muted", 12, weight=500))
        body.append(text(x + 18, top + 58, name, "ink", 19, weight=600))
        body.append(text(x + 18, top + 82, l1, "ink2", 13))
        body.append(text(x + 18, top + 99, l2, "ink2", 13))
        if human:
            body.append(text(x + bw / 2, top + 140, "A person decides", "amber", 12, "middle", 600))
        if i < 4:
            ax = x + bw + 6
            body.append(line(ax, top + 56, ax + gap - 12, top + 56, "grey", 1.5))
            body.append(f'<path d="M{ax + gap - 12:.1f},{top + 51} l7,5 l-7,5z" fill="{LIGHT["grey"]}" class="f-grey"/>')
    body.append(text(2, 18, "Machines compute. People decide what it means and whether to believe it.", "muted", 13))
    return svg(W, H, body, "The TopicLLM workflow",
               "Five stages: discover, name, define, check, report. People decide at discover, define and check.")


def unique_candidates() -> list[dict]:
    runs = json.loads((DATA / "all_iteration_results.json").read_text(encoding="utf-8"))["iterations"]
    seen, out = set(), []
    for it in runs:
        for d in it["details"]:
            if d.get("status") != "scored":
                continue
            key = (it["iteration"], tuple(sorted(d["topic_sizes"].values())))
            if key in seen:
                continue
            seen.add(key)
            out.append({"iteration": it["iteration"], "max_topics": d["max_topics"], "k": d["n_topics_found"],
                        "cv": d["coherence"], "largest": d["largest_topic_share_of_assigned"]})
    return out


def fig_selection() -> str:
    """Coherence against number of topics; the degenerate winner and the selected solution."""
    cands = unique_candidates()
    W, H = 960, 440
    L, R, T, B = 72, 24, 40, 64
    xmin, xmax, ymin, ymax = 1, 25, 0.20, 0.65
    X = lambda k: L + (k - xmin) / (xmax - xmin) * (W - L - R)
    Y = lambda v: T + (ymax - v) / (ymax - ymin) * (H - T - B)
    body = []
    for v in [0.2, 0.3, 0.4, 0.5, 0.6]:
        body.append(line(L, Y(v), W - R, Y(v), "rule"))
        body.append(text(L - 10, Y(v) + 5, f"{v:.1f}", "muted", 12, "end"))
    for k in [2, 5, 10, 15, 20, 24]:
        body.append(text(X(k), H - B + 22, str(k), "muted", 12, "middle"))
    body.append(text((L + W - R) / 2, H - 18, "Topics in the solution", "ink2", 13, "middle"))
    body.append(text(18, T + (H - T - B) / 2, "Coherence (cᵥ)", "ink2", 13, "middle",
                     extra=f'transform="rotate(-90 18 {T + (H - T - B) / 2:.1f})"'))
    # Deterministic horizontal jitter so integer topic counts don't overplot.
    for c in sorted(cands, key=lambda c: c["largest"] <= 0.5):
        jitter = ((c["iteration"] * 37 + c["max_topics"] * 11) % 21 - 10) / 34
        role = "accent" if c["largest"] <= 0.5 else "grey"
        body.append(f'<circle cx="{X(c["k"] + jitter):.1f}" cy="{Y(c["cv"]):.1f}" r="3" fill="{LIGHT[role]}" '
                    f'class="f-{role}" fill-opacity="{0.55 if role == "accent" else 0.45}"/>')
    winner = max(cands, key=lambda c: c["cv"])
    chosen = max((c for c in cands if c["largest"] <= 0.5), key=lambda c: c["cv"])
    wx, wy = X(winner["k"]), Y(winner["cv"])
    cx, cy = X(chosen["k"]), Y(chosen["cv"])
    body += [circle(wx, wy, 9, None, "ink", 2), circle(cx, cy, 9, None, "amber", 2.5)]
    body.append(line(wx + 10, wy - 2, wx + 58, wy - 14, "ink", 1))
    body.append(text(wx + 62, wy - 24, "Highest score: 2 topics,", "ink", 13, weight=600))
    body.append(text(wx + 62, wy - 8, f"{pct(winner['largest'], 1)} of posts in one", "ink2", 13))
    ly = Y(0.625)
    body.append(line(cx + 6, cy - 8, cx + 40, ly + 8, "amber", 1))
    body.append(text(cx + 44, ly, f"Selected: highest score where no topic holds a majority", "amber", 13, weight=600))
    body.append(text(cx + 44, ly + 16, f"{chosen['k']} topics; the largest holds {pct(chosen['largest'])} of posts", "ink2", 13))
    lx = W - R - 360
    body += [circle(lx, 22, 4, "accent"), text(lx + 10, 27, "No topic holds a majority", "ink2", 12),
             circle(lx + 190, 22, 4, "grey"), text(lx + 200, 27, "One topic holds most posts", "ink2", 12)]
    body.append(text(L, 26, f"{len(cands)} distinct candidate solutions", "muted", 12))
    return svg(W, H, body, "Choosing a topic solution",
               "Coherence against number of topics for every candidate. The highest-coherence solution has two topics "
               "with 99.5% of posts in one; the highest-coherence solution in which no topic holds a majority has 12 topics.")


def prevalence_rows() -> tuple[dict, list[dict]]:
    data = json.loads((DATA / "human_sample_prevalence.json").read_text(encoding="utf-8"))
    return data, data["themes"]


def fig_finding() -> str:
    """Human-coded random sample: share of first-term posts per theme with 95% CIs."""
    data, rows = prevalence_rows()
    rowh, top, L, R = 36, 50, 250, 70
    W = 960
    H = top + rowh * len(rows) + 52
    scale = lambda v: L + v / 0.45 * (W - L - R)
    body = []
    for v in [0, 0.1, 0.2, 0.3, 0.4]:
        body.append(line(scale(v), top - 8, scale(v), top + rowh * len(rows), "rule"))
        body.append(text(scale(v), top + rowh * len(rows) + 22, pct(v), "muted", 12, "middle"))
    for i, r in enumerate(rows):
        y = top + i * rowh + rowh / 2
        h = r["human_sample"]
        resid = r["residual"]
        role = "grey" if resid else "accent"
        body.append(text(L - 16, y + 5, SHORT[r["theme"]], "muted" if resid else "ink", 14, "end",
                         600 if i == 0 else 400))
        lo, hi = h["wilson_95"]
        body.append(line(scale(lo), y, scale(hi), y, role, 2.5))
        body.append(circle(scale(h["share"]), y, 6.5, role))
        label = f"0 of {h['of']}" if h["posts"] == 0 else pct(h["share"])
        body.append(text(scale(hi) + 10, y + 5, label, "ink2", 13, weight=600 if i == 0 else 400))
    body.append(text(L, 22, "Share of first-term posts (dot) with 95% confidence interval (line)", "muted", 12))
    body.append(text(L, H - 6, f"Two people coded a random sample of {rows[0]['human_sample']['of']} of 26,239 posts.",
                     "muted", 12))
    return svg(W, H, body, "What two human coders found",
               "Share of Donald Trump's first-term posts expressing each campaign theme, from a human-coded random "
               "sample of 250 posts, with 95% confidence intervals.")


def fig_proof() -> str:
    """The residual on the same 250 posts (humans vs classifier), plus the classifier on all posts."""
    data, rows = prevalence_rows()
    human = data["headline"]["human_residual_share"]
    same = data["headline"]["classifier_residual_share_in_sample"]
    model = data["headline"]["classifier_residual_share"]
    W, H, L, R = 960, 250, 280, 90
    scale = lambda v: (W - L - R) * v / 0.45
    body = [text(0, 22, "Posts that fit no campaign theme", "ink", 16, weight=600)]
    bars = [("Two human coders · 250 posts", human, "accent"), ("Classifier · the same 250 posts", same, "amber"),
            ("Classifier · all 26,239 posts", model, "grey")]
    for i, (label, value, role) in enumerate(bars):
        y = 46 + i * 58
        body.append(text(L - 16, y + 25, label, "ink", 15, "end", 500))
        body.append(rect(L, y, W - L - R, 36, "greysoft", rx=6))
        body.append(rect(L, y, scale(value), 36, role, rx=6))
        body.append(text(L + scale(value) + 12, y + 25, pct(value), "ink2" if role == "grey" else role, 19, weight=700))
    body.append(text(L, H - 10, "Human coders and classifier on one random sample of first-term posts; grey: the classifier on every post.", "muted", 12))
    return svg(W, H, body, "The check that caught the classifier",
               f"Share of first-term posts that fit no campaign theme. On the same 250 posts: {pct(human)} by two human coders, "
               f"{pct(same)} by the classifier. On all 26,239 posts the classifier said {pct(model)}.")


def fig_compare() -> str:
    """Per theme: human sample vs the classifier's corpus shares."""
    data, rows = prevalence_rows()
    rowh, top, L, R, W = 44, 56, 250, 70, 960
    H = top + rowh * len(rows) + 40
    scale = lambda v: (W - L - R) * v / 0.45
    body = []
    for v in [0, 0.1, 0.2, 0.3, 0.4]:
        x = L + scale(v)
        body.append(line(x, top - 6, x, top + rowh * len(rows), "rule"))
        body.append(text(x, top + rowh * len(rows) + 22, pct(v), "muted", 12, "middle"))
    for i, r in enumerate(rows):
        y = top + i * rowh
        if r["residual"]:
            body.append(rect(0, y - 3, W, rowh, "ambersoft", rx=6))
        body.append(text(L - 16, y + 22, SHORT[r["theme"]], "ink", 14, "end"))
        h, c = r["human_sample"]["share"], r["classifier"]["share"]
        body.append(rect(L, y + 6, scale(h), 13, "accent", rx=3))
        body.append(rect(L, y + 21, scale(c), 13, "grey", rx=3))
        body.append(text(L + scale(h) + 8, y + 17, "0 of 250" if h == 0 else pct(h), "ink2", 12))
        body.append(text(L + scale(c) + 8, y + 32, pct(c), "muted", 12))
    body += [rect(L, 18, 14, 12, "accent", rx=2), text(L + 20, 29, "Two human coders (random sample, n = 250)", "ink2", 12),
             rect(L + 300, 18, 14, 12, "grey", rx=2),
             text(L + 320, 29, "Classifier, all 26,239 posts (model-assigned)", "ink2", 12)]
    return svg(W, H, body, "Humans and the classifier, theme by theme",
               "For each theme, the human-coded sample share and the classifier's model-assigned share of all "
               "first-term posts. The classifier sends far more posts to 'fits no theme'.")


def fig_confusion() -> str:
    """Confusion matrix of the held-out check (rows: human consensus; columns: classifier)."""
    report = json.loads((DATA / "evaluation_report.json").read_text(encoding="utf-8"))
    conf = report["metrics"]["confusion"]
    _, rows = prevalence_rows()
    order = [r["theme"] for r in rows]
    order = order[-1:] + order[:-1]  # "Fits no theme" first, so the main error column is visible on any screen
    n = len(order)
    cell, L, T = 40, 200, 170
    W, H = L + cell * n + 130, T + cell * n + 60
    peak = max(conf[h][p] for h in order for p in order if h != p) or 1
    body = []
    for j, p in enumerate(order):
        x = L + j * cell + cell / 2
        body.append(text(x, T - 10, SHORT[p], "ink2", 12, "start",
                         extra=f'transform="rotate(-50 {x:.1f} {T - 10})"'))
    for i, h in enumerate(order):
        y = T + i * cell
        body.append(text(L - 10, y + cell / 2 + 5, SHORT[h], "ink2", 12, "end"))
        for j, p in enumerate(order):
            x = L + j * cell
            v = conf[h][p]
            if i == j:
                body.append(rect(x + 1, y + 1, cell - 2, cell - 2, "accentsoft" if v else "greysoft", rx=4,
                                 stroke="accent" if v else None))
            elif v:
                op = 0.25 + 0.75 * v / peak
                role = "amber"
                body.append(f'<rect x="{x + 1}" y="{y + 1}" width="{cell - 2}" height="{cell - 2}" rx="4" '
                            f'fill="{LIGHT[role]}" class="f-{role}" fill-opacity="{op:.2f}"/>')
            else:
                body.append(rect(x + 1, y + 1, cell - 2, cell - 2, "greysoft", rx=4))
            if v:
                role = "ink" if (i == j or v / peak < 0.5) else "bg"
                body.append(text(x + cell / 2, y + cell / 2 + 5, str(v), role, 13, "middle", 600))
    body.append(text(L, H - 26, "Rows: what the two human coders agreed. Columns: what the classifier said.", "muted", 12))
    body.append(text(L, H - 8, "Diagonal = agreement (175 of 250). Amber = disagreement; the first column holds 45 of the 75 misses.", "muted", 12))
    return svg(W, H, body, "Where the classifier disagreed with the human coders",
               "Confusion matrix for the 250 held-out posts. Most disagreements are human-coded theme posts that the "
               "classifier sent to 'fits no theme'.")


def fig_naming() -> str:
    """Topic 0: the 500-vote tally (top wordings)."""
    with (DATA / "vote_tallies.csv").open(encoding="utf-8", newline="") as handle:
        tally = [r for r in csv.DictReader(handle) if r["topic"] == "0"]
    tally.sort(key=lambda r: -int(r["votes"]))
    top = tally[:6]
    rest = sum(int(r["votes"]) for r in tally[6:])
    W, L, R, rowh = 960, 470, 60, 34
    H = 46 + rowh * (len(top) + 1) + 30
    total = sum(int(r["votes"]) for r in tally)
    scale = lambda v: (W - L - R) * v / 200
    body = [text(0, 22, "Topic 0 · poll, debate, trump, cruz, rubio, jeb, ted …", "ink", 15, weight=600)]
    for i, r in enumerate(top + [{"norm": f"{len(tally) - 6} other wordings", "votes": rest}]):
        y = 44 + i * rowh
        v = int(r["votes"])
        role = "accent" if i == 0 else "grey"
        label = r["norm"] if len(r["norm"]) <= 56 else r["norm"][:55] + "…"
        body.append(text(L - 14, y + 18, label, "ink" if i == 0 else "ink2", 13, "end", 600 if i == 0 else 400))
        body.append(rect(L, y + 5, scale(v), 18, role, rx=3))
        body.append(text(L + scale(v) + 8, y + 19, str(v), "ink2", 12))
    body.append(text(L, H - 8, f"{total} calls to the same model. The top wording is a proposal, not a decision.", "muted", 12))
    return svg(W, H, body, "Asking an LLM 500 times", "Vote tally for topic 0's name across 500 model calls.")


# ------------------------------------------------- phone-width variants ---
# Labels sit above their marks so text stays legible at 390 px.

def fig_finding_narrow() -> str:
    data, rows = prevalence_rows()
    W, L, R, rowh, top = 400, 4, 52, 46, 36
    H = top + rowh * len(rows) + 40
    scale = lambda v: 16 + v / 0.45 * (W - 16 - R)
    body = [text(L, 16, "Share of first-term posts, 95% CI", "muted", 13)]
    for v in [0, 0.2, 0.4]:
        body.append(line(scale(v), top, scale(v), top + rowh * len(rows), "rule"))
        body.append(text(scale(v), top + rowh * len(rows) + 20, pct(v), "muted", 12, "middle"))
    for i, r in enumerate(rows):
        y = top + i * rowh
        h = r["human_sample"]
        role = "grey" if r["residual"] else "accent"
        body.append(text(L, y + 16, SHORT[r["theme"]], "muted" if r["residual"] else "ink", 15, weight=600 if i == 0 else 400))
        lo, hi = h["wilson_95"]
        body.append(line(scale(lo), y + 32, scale(hi), y + 32, role, 3))
        body.append(circle(scale(h["share"]), y + 32, 7, role))
        label = f"0 of {h['of']}" if h["posts"] == 0 else pct(h["share"])
        body.append(text(scale(hi) + 8, y + 37, label, "ink2", 14, weight=600 if i == 0 else 400))
    return svg(W, H, body, "What two human coders found",
               "Share of first-term posts per campaign theme, human-coded random sample of 250, with 95% intervals.")


def fig_proof_narrow() -> str:
    data, rows = prevalence_rows()
    human = data["headline"]["human_residual_share"]
    same = data["headline"]["classifier_residual_share_in_sample"]
    model = data["headline"]["classifier_residual_share"]
    W, H, L = 400, 290, 4
    scale = lambda v: (W - 70) * v / 0.45
    body = [text(L, 18, "Posts that fit no campaign theme", "ink", 16, weight=600)]
    bars = [("Two human coders · 250 posts", human, "accent"), ("Classifier · the same 250 posts", same, "amber"),
            ("Classifier · all 26,239 posts", model, "grey")]
    for i, (label, value, role) in enumerate(bars):
        y = 40 + i * 76
        body.append(text(L, y + 14, label, "ink", 14, weight=500))
        body.append(rect(L, y + 22, W - 70, 32, "greysoft", rx=6))
        body.append(rect(L, y + 22, scale(value), 32, role, rx=6))
        body.append(text(L + scale(value) + 8, y + 45, pct(value), "ink2" if role == "grey" else role, 17, weight=700))
    return svg(W, H, body, "The check that caught the classifier",
               f"Fits no campaign theme on the same 250 posts: {pct(human)} by two human coders, {pct(same)} by the classifier; "
               f"{pct(model)} by the classifier on all posts.")


def fig_compare_narrow() -> str:
    data, rows = prevalence_rows()
    W, L, R, rowh, top = 400, 4, 52, 58, 52
    H = top + rowh * len(rows) + 16
    scale = lambda v: (W - L - R) * v / 0.45
    body = [rect(L, 8, 12, 12, "accent", rx=2), text(L + 18, 19, "Two human coders (n = 250)", "ink2", 13),
            rect(L, 28, 12, 12, "grey", rx=2), text(L + 18, 39, "Classifier, all posts (model-assigned)", "ink2", 13)]
    for i, r in enumerate(rows):
        y = top + i * rowh
        if r["residual"]:
            body.append(rect(0, y - 4, W, rowh, "ambersoft", rx=6))
        h, c = r["human_sample"]["share"], r["classifier"]["share"]
        body.append(text(L, y + 14, SHORT[r["theme"]], "ink", 15))
        body.append(rect(L, y + 22, scale(h), 12, "accent", rx=3))
        body.append(rect(L, y + 37, scale(c), 12, "grey", rx=3))
        body.append(text(L + scale(h) + 6, y + 32, "0 of 250" if h == 0 else pct(h), "ink2", 12))
        body.append(text(L + scale(c) + 6, y + 47, pct(c), "muted", 12))
    return svg(W, H, body, "Humans and the classifier, theme by theme",
               "Per theme: human-coded sample share and classifier model-assigned share of all first-term posts.")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    figures = {"pipeline": fig_pipeline(), "selection": fig_selection(), "finding": fig_finding(),
               "proof": fig_proof(), "compare": fig_compare(), "confusion": fig_confusion(), "naming": fig_naming(),
               "finding-narrow": fig_finding_narrow(), "proof-narrow": fig_proof_narrow(),
               "compare-narrow": fig_compare_narrow()}
    for name, content in figures.items():
        (OUT / f"{name}.svg").write_text(content, encoding="utf-8", newline="\n")
        print(f"wrote docs/assets/figures/{name}.svg")


if __name__ == "__main__":
    main()
