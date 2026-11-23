"""Estimate first-term theme prevalence from the human-coded random sample.

The 250 held-out posts are a simple random sample (without replacement) of the
26,239 first-term posts. Two people coded every post independently and then
adjudicated their differences. Their consensus labels are therefore a direct,
design-based estimate of how often each theme occurs; no classifier is needed.

This script uses only the published aggregate confusion counts, so anyone can
rerun it without private post-level labels or API calls:

    python scripts/estimate-human-sample-prevalence.py

It writes docs/data/trump/campaign/human_sample_prevalence.json with three
views of the same question:

1. human_sample   : consensus label counts / 250, with 95% Wilson intervals
                    (finite-population corrected).
2. classifier     : the unchanged classifier's full-corpus shares (unvalidated).
3. calibrated     : the classifier's corpus counts redistributed with
                    P(human label | classifier label) estimated from the same
                    sample, with a seeded bootstrap interval over the 250 pairs.

The human sample is the primary estimate. The calibrated view illustrates how a
measured error profile changes a classifier's raw output; it assumes the
sample's error pattern holds across the corpus.
"""
from __future__ import annotations

import csv
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / "docs" / "data" / "trump" / "campaign"
RESIDUAL = "The text does not fit into any of these themes"
N_POPULATION = 26239
BOOTSTRAP_DRAWS = 4000
SEED = 20261123


def wilson(k: int, n: int, z: float = 1.959963984540054, population: int | None = None) -> list[float]:
    """Wilson score interval, optionally with a finite-population correction."""
    if n == 0:
        return [float("nan"), float("nan")]
    p = k / n
    fpc = math.sqrt((population - n) / (population - 1)) if population else 1.0
    z = z * fpc
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [max(0.0, centre - half), min(1.0, centre + half)]


def calibrate(confusion: dict, labels: list[str], corpus: dict[str, int]) -> dict[str, float]:
    """Redistribute corpus predictions using P(human | predicted) from the sample.

    Predicted labels never produced in the sample keep their own label, because
    the sample carries no information about where those posts belong.
    """
    total = sum(corpus.values())
    estimate = {label: 0.0 for label in labels}
    for predicted in labels:
        column = {human: confusion[human][predicted] for human in labels}
        column_n = sum(column.values())
        if column_n == 0:
            estimate[predicted] += corpus[predicted]
            continue
        for human, count in column.items():
            estimate[human] += corpus[predicted] * count / column_n
    return {label: value / total for label, value in estimate.items()}


def main() -> None:
    report = json.loads((CAMPAIGN / "evaluation_report.json").read_text(encoding="utf-8"))
    confusion = report["metrics"]["confusion"]  # confusion[human][predicted]
    labels = list(confusion)
    n = sum(sum(row.values()) for row in confusion.values())
    assert n == report["n_benchmark"] == 250, "The published sample must contain 250 posts."

    with (CAMPAIGN / "theme_counts.csv").open(encoding="utf-8", newline="") as handle:
        corpus = {row["theme"]: int(row["documents"]) for row in csv.DictReader(handle)}
    assert set(corpus) == set(labels) and sum(corpus.values()) == N_POPULATION

    human_counts = {label: sum(confusion[label].values()) for label in labels}
    calibrated = calibrate(confusion, labels, corpus)

    # Bootstrap the 250 (human, predicted) pairs, which the confusion counts fully describe.
    pairs = [(h, p) for h in labels for p in labels for _ in range(confusion[h][p])]
    rng = random.Random(SEED)
    draws = {label: [] for label in labels}
    covered = []
    for _ in range(BOOTSTRAP_DRAWS):
        sample = [pairs[rng.randrange(n)] for _ in range(n)]
        boot = {h: {p: 0 for p in labels} for h in labels}
        for h, p in sample:
            boot[h][p] += 1
        estimate = calibrate(boot, labels, corpus)
        for label in labels:
            draws[label].append(estimate[label])
        covered.append(1 - estimate[RESIDUAL])

    def percentile(values: list[float], q: float) -> float:
        ordered = sorted(values)
        return ordered[min(len(ordered) - 1, max(0, round(q * (len(ordered) - 1))))]

    rows = []
    for label in labels:
        k = human_counts[label]
        rows.append({
            "theme": label,
            "residual": label == RESIDUAL,
            "human_sample": {"posts": k, "of": n, "share": k / n, "wilson_95": wilson(k, n, population=N_POPULATION)},
            "classifier": {"posts": corpus[label], "of": N_POPULATION, "share": corpus[label] / N_POPULATION, "validated": False},
            "calibrated": {"share": calibrated[label], "bootstrap_95": [percentile(draws[label], 0.025), percentile(draws[label], 0.975)]},
        })
    rows.sort(key=lambda r: (r["residual"], -r["human_sample"]["share"]))

    themed = n - human_counts[RESIDUAL]
    result = {
        "schema_version": 1,
        "question": "What share of Donald Trump's first-term posts express each theme discovered in his 2015-2016 campaign posts?",
        "design": "Simple random sample without replacement of 250 of the 26,239 first-term posts (2017-01-20 to 2021-01-08). Two independent human coding passes, then adjudication of all 80 differences.",
        "primary_estimate": "human_sample",
        "headline": {
            "fits_a_campaign_theme": {"posts": themed, "of": n, "share": themed / n, "wilson_95": wilson(themed, n, population=N_POPULATION)},
            "largest_theme": rows[0]["theme"],
            "largest_theme_share": rows[0]["human_sample"]["share"],
            "largest_theme_wilson_95": rows[0]["human_sample"]["wilson_95"],
            "classifier_residual_share": corpus[RESIDUAL] / N_POPULATION,
            "classifier_residual_share_in_sample": sum(confusion[h][RESIDUAL] for h in labels) / n,
            "human_residual_share": human_counts[RESIDUAL] / n,
            "calibrated_fits_a_campaign_theme": 1 - calibrated[RESIDUAL],
            "calibrated_fits_bootstrap_95": [percentile(covered, 0.025), percentile(covered, 0.975)],
        },
        "human_coder_agreement": report["independent_human_agreement"]["agreement"],
        "human_coder_kappa": report["independent_human_agreement"]["cohens_kappa"],
        "classifier_agreement": report["metrics"]["agreement"],
        "themes": rows,
        "method": {
            "interval": "Wilson score, 95%, finite-population corrected (N=26,239, n=250).",
            "calibration": "Corpus classifier counts redistributed by P(human label | classifier label) estimated from the 250 sample pairs; predicted labels absent from the sample keep their label.",
            "bootstrap": f"{BOOTSTRAP_DRAWS} resamples of the 250 pairs, seed {SEED}, percentile interval.",
            "inputs": ["evaluation_report.json (aggregate confusion counts)", "theme_counts.csv (classifier corpus counts)"],
        },
        "limits": [
            "Human coders agreed on 68% of posts before adjudication (kappa 0.61); adjudicated labels are a working reference, not error-free truth.",
            "Themes with fewer than about ten sampled posts have wide intervals.",
            "Posting events include retweets and staff-mediated posts; shares describe the archived account, not public opinion.",
            "The calibrated view assumes the sample's error pattern holds across the corpus.",
        ],
    }
    out = CAMPAIGN / "human_sample_prevalence.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Human-coded random sample: n={n} of N={N_POPULATION}")
    head = result["headline"]["fits_a_campaign_theme"]
    print(f"  Fits a campaign theme: {head['share']:.1%} (95% CI {head['wilson_95'][0]:.1%}-{head['wilson_95'][1]:.1%})")
    for r in rows:
        h, c, k = r["human_sample"], r["classifier"], r["calibrated"]
        print(f"  {r['theme'][:58]:<58} human {h['share']:6.1%} [{h['wilson_95'][0]:5.1%}-{h['wilson_95'][1]:5.1%}]"
              f"  classifier {c['share']:6.1%}  calibrated {k['share']:6.1%} [{k['bootstrap_95'][0]:5.1%}-{k['bootstrap_95'][1]:5.1%}]")
    print(f"Wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
