"""
stage5_inference.py — From classifications to theme prevalence (Stage 5).

The primary output is overall target-corpus prevalence: counts and shares for
every approved theme and the residual, including zero-count categories. The
campaign-to-presidency application verifies exact target ID coverage and a
current accepted classifier before computing these descriptive proportions.
Period comparisons are an explicit opt-in extension, disabled for this study;
they require dates and use Bonferroni-adjusted proportional z-tests.

Inputs   : pipeline_output/stage4/classified_corpus.csv
Artifacts: pipeline_output/stage5/
             theme_counts.csv
             prevalence_by_period.csv
             ztest_results.csv
"""

import os
import json
import hashlib
from pathlib import Path
from itertools import combinations

import pandas as pd
from statsmodels.stats.proportion import proportions_ztest

if __package__:
    from .config import CONFIG
else:
    from config import CONFIG
if __package__:
    from .llm_backend import ERROR_LABEL
else:
    from llm_backend import ERROR_LABEL


def run_stage5(cfg=CONFIG) -> str:
    out = os.path.join(cfg.output_dir, "stage5")
    os.makedirs(out, exist_ok=True)
    corpus = pd.read_csv(os.path.join(cfg.output_dir, "stage4", "classified_corpus.csv"))
    if cfg.demonstration_exception_path:
        if __package__:from .demonstration import require_demonstration_exception
        else:from demonstration import require_demonstration_exception
        require_demonstration_exception(cfg)
    if cfg.require_disjoint_windows:
        if __package__:
            from .research_validation import require_validation_review
            from .sampling import read_selected
        else:
            from research_validation import require_validation_review
            from sampling import read_selected
        if not cfg.demonstration_exception_path:require_validation_review(cfg)
        selected, selection = read_selected(cfg, 'target')
        if len(corpus) != len(selected) or set(corpus.post_id.astype(str)) != {r['post_id'] for r in selected}:
            raise ValueError('Classifications do not exhaust the declared target corpus exactly.')

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
    if cfg.run_pairwise_tests and len(ranges) < 2:
        raise ValueError("Pairwise tests require at least two non-overlapping periods.")
    for i,(name,(start,end)) in enumerate(ranges):
        if not name or pd.Timestamp(start) > pd.Timestamp(end):
            raise ValueError("Invalid period definition.")
        for _,(other_start,other_end) in ranges[i+1:]:
            if start <= other_end and other_start <= end:
                raise ValueError("Period ranges overlap.")

    # ---- 1. Whole-corpus theme prevalence ----------------------------------
    counts = corpus["theme"].value_counts().reindex(cfg.themes + [cfg.none_label], fill_value=0)
    theme_rows = [{"theme": theme, "documents": int(n),
                   "denominator": len(corpus), "share": n / len(corpus)}
                  for theme, n in counts.items()]
    pd.DataFrame(theme_rows).to_csv(os.path.join(out, "theme_counts.csv"), index=False)
    input_path=Path(cfg.output_dir,'stage4','classified_corpus.csv')
    Path(out,'estimand.json').write_text(json.dumps({
        'unit':'posting event','denominator':len(corpus),'target_window':cfg.target_window,
        'periods':cfg.periods,'pairwise_tests':cfg.run_pairwise_tests,
        'classified_corpus_sha256':hashlib.sha256(input_path.read_bytes()).hexdigest(),
        'model_mode':'MOCK' if cfg.llm_backend=='mock' else 'unvalidated-demonstration' if cfg.demonstration_exception_path else 'research',
        'classifier_validated':False if cfg.demonstration_exception_path or cfg.llm_backend=='mock' else bool(cfg.require_disjoint_windows),
        'interpretation':'Engineering output only; not research findings.' if cfg.llm_backend=='mock' else 'Unvalidated model-assigned shares for methodological illustration. Held-out acceptance criteria failed; these are not validated theme prevalence estimates.' if cfg.demonstration_exception_path else 'Descriptive classifier-assigned shares of archived account posts; no causal or public-opinion inference.'
    },indent=2),encoding='utf-8')
    print(f"[stage5] Whole-corpus prevalence written for {len(theme_rows)} labels "
          f"({len(corpus):,} documents).")

    # ---- 2. Prevalence by period + proportional z-tests --------------------
    if "date" in corpus.columns and cfg.periods:
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
        period_pairs = list(combinations(cfg.periods.keys(), 2)) if cfg.run_pairwise_tests else []
        # Bonferroni: alpha / (n_themes x tests per theme) — reference design
        # runs 3 pairwise tests per theme (pre-peri, peri-post, pre-post).
        alpha_adj = cfg.alpha / (len(cfg.themes) * len(period_pairs)) if period_pairs else None

        long_rows=[]
        for theme in cfg.themes + [cfg.none_label]:
            counts = (in_period.assign(hit=in_period["theme"] == theme)
                      .groupby("period")["hit"].sum())
            row = {"theme": theme}
            for p in cfg.periods:
                n, k = int(totals.get(p, 0)), int(counts.get(p, 0))
                row[f"{p}_pct"] = round(100 * k / n, 2) if n else None
                row[f"{p}_n"] = n
                row[f"{p}_k"] = k
                long_rows.append({'period':p, 'theme':theme, 'documents':k, 'denominator':n, 'share':k/n})
            prev_rows.append(row)

            for a, b in period_pairs if theme in cfg.themes else []:
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
        pd.DataFrame(long_rows).to_csv(os.path.join(out, "prevalence_long.csv"), index=False)
        if test_rows: pd.DataFrame(test_rows).to_csv(os.path.join(out, "ztest_results.csv"), index=False)
        elif Path(out,'ztest_results.csv').exists(): Path(out,'ztest_results.csv').unlink()
        print(f"[stage5] Prevalence table and {len(test_rows)} z-tests written.")
    else:
        print("[stage5] No 'date' column — skipping period prevalence/z-tests.")

    print(f"[stage5] DONE — artifacts in {out}/")
    return out


if __name__ == "__main__":
    run_stage5()
