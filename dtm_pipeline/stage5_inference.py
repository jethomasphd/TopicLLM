"""
stage5_inference.py — From classifications to theme prevalence (Stage 5).

The pipeline terminates in the statistic that motivates it: theme prevalence.
  1. Whole-corpus theme prevalence — document counts and shares per theme.
  2. Proportional z-tests comparing theme prevalence across periods, with a
     Bonferroni correction of alpha / (n_themes x tests_per_theme). Requires
     a 'date' column in the source CSV; skipped otherwise.

Inputs   : pipeline_output/stage4/classified_corpus.csv
Artifacts: pipeline_output/stage5/
             theme_counts.csv
             prevalence_by_period.csv
             ztest_results.csv
"""

import os
from itertools import combinations

import pandas as pd
from statsmodels.stats.proportion import proportions_ztest

from config import CONFIG
from llm_backend import ERROR_LABEL


def run_stage5(cfg=CONFIG) -> str:
    out = os.path.join(cfg.output_dir, "stage5")
    os.makedirs(out, exist_ok=True)
    corpus = pd.read_csv(os.path.join(cfg.output_dir, "stage4", "classified_corpus.csv"))

    allowed = set(cfg.themes + [cfg.none_label])
    if corpus.empty or not cfg.themes or len(set(cfg.themes)) != len(cfg.themes):
        raise ValueError("A non-empty corpus and unique themes are required.")
    if not corpus["theme"].isin(allowed).all():
        raise ValueError("Resolve failed, missing or invalid classifications before estimating prevalence.")
    if "status" in corpus and corpus["status"].isin(["error","unmatched","empty"]).any():
        raise ValueError("Unresolved classifications are not measurements.")
    if not 0 < cfg.alpha < 1:
        raise ValueError("Alpha must be between zero and one.")
    ranges = list(cfg.periods.items())
    if len(ranges) < 2:
        raise ValueError("Define at least two non-overlapping periods.")
    for i,(name,(start,end)) in enumerate(ranges):
        if not name or pd.Timestamp(start) > pd.Timestamp(end):
            raise ValueError("Invalid period definition.")
        for _,(other_start,other_end) in ranges[i+1:]:
            if start <= other_end and other_start <= end:
                raise ValueError("Period ranges overlap.")

    # ---- 1. Whole-corpus theme prevalence ----------------------------------
    counts = corpus["theme"].value_counts()
    theme_rows = [{"theme": theme, "documents": int(n),
                   "share": round(n / len(corpus), 4)}
                  for theme, n in counts.items()]
    pd.DataFrame(theme_rows).to_csv(os.path.join(out, "theme_counts.csv"), index=False)
    print(f"[stage5] Whole-corpus prevalence written for {len(theme_rows)} labels "
          f"({len(corpus):,} documents).")

    # ---- 2. Prevalence by period + proportional z-tests --------------------
    if "date" in corpus.columns:
        corpus["date"] = pd.to_datetime(corpus["date"], errors="coerce", utc=True).dt.tz_convert(None).dt.normalize()
        if corpus["date"].isna().any():
            raise ValueError("Missing or invalid document dates.")
        corpus["period"] = None
        for name, (start, end) in cfg.periods.items():
            mask = corpus["date"].between(pd.Timestamp(start), pd.Timestamp(end))
            corpus.loc[mask, "period"] = name
        in_period = corpus.dropna(subset=["period"])
        print(f"[stage5] {len(in_period):,} documents fall in the defined periods "
              f"({len(corpus) - len(in_period):,} outside them, e.g. between periods).")

        totals = in_period.groupby("period").size()
        if any(totals.get(p,0) == 0 for p in cfg.periods):
            raise ValueError("At least one declared period has no documents.")
        prev_rows, test_rows = [], []
        period_pairs = list(combinations(cfg.periods.keys(), 2))
        # Bonferroni: alpha / (n_themes x tests per theme) — reference design
        # runs 3 pairwise tests per theme (pre-peri, peri-post, pre-post).
        alpha_adj = cfg.alpha / (len(cfg.themes) * len(period_pairs))
        print(f"[stage5] Bonferroni-adjusted alpha = {cfg.alpha} / "
              f"({len(cfg.themes)} themes x {len(period_pairs)} tests) = {alpha_adj:.4f}")

        for theme in cfg.themes:
            counts = (in_period.assign(hit=in_period["theme"] == theme)
                      .groupby("period")["hit"].sum())
            row = {"theme": theme}
            for p in cfg.periods:
                n, k = int(totals.get(p, 0)), int(counts.get(p, 0))
                row[f"{p}_pct"] = round(100 * k / n, 2) if n else None
                row[f"{p}_n"] = n
            prev_rows.append(row)

            for a, b in period_pairs:
                ka, na = int(counts.get(a, 0)), int(totals.get(a, 0))
                kb, nb = int(counts.get(b, 0)), int(totals.get(b, 0))
                if min(na, nb) == 0:
                    continue
                # Ordered (b, a) so z > 0 means prevalence rose from period a
                # to period b — the same direction as pct_change and as the
                # dissertation's reported statistics.
                estimable = 0 < ka + kb < na + nb
                z, p_val = proportions_ztest([kb, ka], [nb, na]) if estimable else (None, None)
                pa, pb = ka / na, kb / nb
                test_rows.append({
                    "theme": theme, "comparison": f"{a} vs {b}",
                    "period_a": a, "k_a": ka, "n_a": na, "prop_a": round(pa, 4),
                    "period_b": b, "k_b": kb, "n_b": nb, "prop_b": round(pb, 4),
                    "pct_change": round(100 * (pb - pa) / pa, 1) if pa else None,
                    "z": round(float(z), 3) if estimable else None, "p": float(p_val) if estimable else None,
                    "sparse_cells": min(ka,na-ka,kb,nb-kb) < 5,
                    "percentage_point_change":100*(pb-pa),
                    "alpha_bonferroni": round(alpha_adj, 6),
                    "significant_bonferroni": bool(estimable and p_val < alpha_adj),
                })

        pd.DataFrame(prev_rows).to_csv(os.path.join(out, "prevalence_by_period.csv"), index=False)
        pd.DataFrame(test_rows).to_csv(os.path.join(out, "ztest_results.csv"), index=False)
        print(f"[stage5] Prevalence table and {len(test_rows)} z-tests written.")
    else:
        print("[stage5] No 'date' column — skipping period prevalence/z-tests.")

    print(f"[stage5] DONE — artifacts in {out}/")
    return out


if __name__ == "__main__":
    run_stage5()
