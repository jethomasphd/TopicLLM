"""Apply the declared Stage 1 selection rule retrospectively to saved candidates.

Reads a saved all_iteration_results.json, collapses ceilings that leave the
same clustering, applies the default rule (selection_rule.py) and writes the
outcome with its sensitivity to the rule's two thresholds. Standard library
plus the package's pure selection module: no ML extra, no API calls.

    python scripts/apply-selection-rule.py
    python scripts/apply-selection-rule.py --results runs/x/stage1/all_iteration_results.json --output out.json

For the recorded Trump tutorial the rule must reproduce the researcher's
inspected choice (iteration 10, max_topics 13, 12 topics); the script exits
nonzero otherwise.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dtm_pipeline.selection_rule import (  # noqa: E402
    dedupe_solutions, flatten_iterations, is_scored, select_candidate, sensitivity, summarize_candidate)

TUTORIAL = ROOT / "docs/data/trump/campaign"
TUTORIAL_RESULTS = TUTORIAL / "all_iteration_results.json"
TUTORIAL_OUTPUT = TUTORIAL / "selection_rule_retrospective.json"
TUTORIAL_EXPECTED = {"iteration": 10, "max_topics": 13, "n_topics": 12}
DISCLOSURE = ("Formalized after the tutorial run, in which the unconstrained coherence winner was degenerate "
              "and the researcher selected this 12-topic candidate by inspection. Applied retrospectively to "
              "every saved solution, the rule selects the same candidate.")


def _display(path: Path) -> str:
    path = path.resolve()
    return path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)


def retrospective(results_path: Path, max_topic_share: float | None = 0.5, min_topics: int = 2) -> dict:
    """Rule outcome, counts and sensitivity for one saved search."""
    results_path = Path(results_path)
    data = json.loads(results_path.read_text(encoding="utf-8"))
    candidates = flatten_iterations(data["iterations"])
    unique = dedupe_solutions(candidates)
    choice = select_candidate(unique, max_topic_share, min_topics)
    grid = sensitivity(unique, max_topic_share=max_topic_share, min_topics=min_topics)
    selected = summarize_candidate(choice["selected"])
    if selected:
        selected.update(umap_params=choice["selected"]["umap_params"], hdbscan_params=choice["selected"]["hdbscan_params"])
    report = {
        "rule": {"text": choice["rule"], "max_topic_share": max_topic_share, "min_topics": min_topics},
        "source": {"path": _display(results_path), "sha256": hashlib.sha256(results_path.read_bytes()).hexdigest()},
        "status": choice["status"],
        "scored_candidates": sum(is_scored(c) for c in candidates),
        "unique_solutions": len(unique),
        "deduplication": "scored candidates keyed by (iteration, sorted topic sizes); best-ranked duplicate kept",
        "admissible_count": choice["admissible_count"],
        "unconstrained_winner": summarize_candidate(choice["unconstrained_winner"]),
        "selected": selected,
        "rule_changed_selection": choice["rule_changed_selection"],
        "sensitivity": {key: grid[key] for key in ("unchanged_grid_range", "unchanged_exact_interval",
                                                   "default_selected_without_cap", "by_max_topic_share",
                                                   "by_min_topics", "by_min_topics_without_cap")},
    }
    record_path = results_path.parent / "selection_record.json"
    if record_path.is_file():
        chosen = json.loads(record_path.read_text(encoding="utf-8"))["selected_candidate"]
        researcher = {"iteration": chosen["iteration"], "max_topics": chosen["max_topics"], "n_topics": chosen["n_topics"]}
        report["researcher_selection"] = {**researcher, "source": _display(record_path)}
        report["matches_researcher_selection"] = bool(selected) and all(selected[k] == v for k, v in researcher.items())
    # The disclosure states a fact about this tutorial; attach it only when that fact holds.
    report["disclosure"] = DISCLOSURE if report.get("matches_researcher_selection") else None
    return report


def _describe(c: dict) -> str:
    return (f"iteration {c['iteration']}, max_topics {c['max_topics']} -> {c['n_topics']} topics, "
            f"c_v {c['coherence']:.4f}, largest topic {c['largest_topic_share_of_assigned']:.1%} of assigned")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--results", type=Path, default=TUTORIAL_RESULTS)
    ap.add_argument("--output", type=Path, default=None, help="default: selection_rule_retrospective.json beside --results")
    args = ap.parse_args()
    report = retrospective(args.results)
    output = args.output or args.results.parent / "selection_rule_retrospective.json"
    tutorial = args.results.resolve() == TUTORIAL_RESULTS.resolve()
    if tutorial and not (report["selected"] and all(report["selected"][k] == v for k, v in TUTORIAL_EXPECTED.items())
                         and report.get("matches_researcher_selection")):
        sys.exit(f"The rule did not reproduce the recorded tutorial choice {TUTORIAL_EXPECTED}; nothing written.")
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")

    s = report["sensitivity"]
    exact = s["unchanged_exact_interval"] or {}
    print(f"Declared rule: {report['rule']['text']}")
    print(f"Saved candidates: {report['scored_candidates']:,} scored; {report['unique_solutions']:,} unique solutions; "
          f"{report['admissible_count']:,} admissible")
    print(f"Unconstrained winner: {_describe(report['unconstrained_winner'])}")
    if report["selected"]:
        print(f"Rule selects:         {_describe(report['selected'])}")
    else:
        print("Rule selects:         nothing admissible (selection_rule_unmet)")
    if "researcher_selection" in report:
        same = "same candidate" if report["matches_researcher_selection"] else "DIFFERENT candidate"
        print(f"Researcher selection ({report['researcher_selection']['source']}): iteration "
              f"{report['researcher_selection']['iteration']}, max_topics {report['researcher_selection']['max_topics']} — {same}")
    if exact:
        cap, floor, alone = exact["max_topic_share"], exact["min_topics"], exact["min_topics_without_cap"]
        upper = "no cap]" if cap["to_exclusive"] is None else f"{cap['to_exclusive']:.4f})"
        print(f"Unchanged for max_topic_share in [{cap['from_inclusive']:.4f}, {upper} "
              f"(grid {s['unchanged_grid_range']['max_topic_share']}); min_topics {floor['from_inclusive']}–{floor['to_inclusive']} "
              f"with the cap" + (f"; the topic floor alone selects it for min_topics {alone['from_inclusive']}–{alone['to_inclusive']}" if alone else ""))
    if report["disclosure"]:
        print(f"Disclosure: {report['disclosure']}")
    print(f"Wrote {_display(output)}")


if __name__ == "__main__":
    main()
