"""Declared admissibility rule for choosing among Stage 1 candidates.

Coherence alone is not a sufficient selection criterion: "attaining high
semantic coherence was relatively easy by having a few topics dominated by
very common words" (Roberts, Stewart & Tingley 2019, JSS), and there is no
single right number of topics (Grimmer & Stewart 2013). In the recorded Trump
tutorial the unconstrained c_v winner was degenerate (2 topics, 99.5% of
assigned posts in one cluster). The rule is therefore declared before the
search: among scored candidates with at least ``min_topics`` topics and no
topic holding more than ``max_topic_share`` of the assigned (non-outlier)
documents, select the highest c_v coherence. The unconstrained winner is
always reported beside the selection, and researchers still inspect the
selected solution's original documents before naming.

Standard library only, so retrospective audits run without the ML extra.
"""
from __future__ import annotations

import math
from collections.abc import Iterable, Sequence

DEFAULT_CAPS = tuple(round(0.30 + 0.05 * i, 2) for i in range(15))  # 0.30 .. 1.00


def rule_text(max_topic_share: float | None, min_topics: int) -> str:
    cap = "no cap on the largest topic" if max_topic_share is None else \
        f"the largest topic holding at most {max_topic_share:g} of assigned (non-outlier) documents"
    return (f"Select the highest c_v coherence among scored candidates with at least {min_topics} "
            f"topics and {cap}; ties go to the earliest iteration, then the smallest max_topics. "
            f"The unconstrained coherence winner is reported alongside.")


def validate_rule(max_topic_share: float | None, min_topics: int) -> None:
    if max_topic_share is not None and (isinstance(max_topic_share, bool) or not isinstance(max_topic_share, (int, float))
                                        or not 0 < max_topic_share <= 1):
        raise ValueError("max_topic_share must be in (0, 1], or null to disable the cap.")
    if isinstance(min_topics, bool) or not isinstance(min_topics, int) or min_topics < 1:
        raise ValueError("min_topics must be a positive integer.")


def is_scored(candidate: dict) -> bool:
    coherence = candidate.get("coherence")
    return (candidate.get("status") == "scored" and isinstance(coherence, (int, float))
            and math.isfinite(coherence))


def is_admissible(candidate: dict, max_topic_share: float | None = 0.5, min_topics: int = 2) -> bool:
    if not is_scored(candidate) or (candidate.get("n_topics_found") or 0) < min_topics:
        return False
    share = candidate.get("largest_topic_share_of_assigned")
    return max_topic_share is None or (share is not None and share <= max_topic_share)


def rank_key(candidate: dict) -> tuple:
    """Sort key: best first. Mirrors the search order, so the first candidate
    to reach a coherence keeps it, as in the original strict '>' comparison."""
    return (-candidate["coherence"], candidate.get("iteration", 0), candidate.get("max_topics", 0))


def outranks(candidate: dict, incumbent: dict | None) -> bool:
    return incumbent is None or rank_key(candidate) < rank_key(incumbent)


def topic_diversity(topic_words: Sequence[Sequence[str]], top_n: int = 10) -> float | None:
    """Unique words / total words over each topic's top-n words. Dieng, Ruiz &
    Blei (2020) use the top 25; BERTopic keeps 10 by default, so ours is
    top-10. Reported for inspection only; not used for selection."""
    words = [w for topic in topic_words for w in list(topic)[:top_n]]
    return len(set(words)) / len(words) if words else None


def flatten_iterations(iterations: Iterable[dict]) -> list[dict]:
    """Per-candidate dicts from all_iteration_results.json records. The
    iteration number and sampled parameters live on the parent record, not
    in each entry of ``details``."""
    return [{"iteration": record["iteration"], "umap_params": record.get("umap_params"),
             "hdbscan_params": record.get("hdbscan_params"), **detail}
            for record in iterations for detail in record.get("details", [])]


def solution_key(candidate: dict) -> tuple:
    sizes = candidate.get("topic_sizes") or {}
    return candidate.get("iteration"), tuple(sorted(sizes.values()))


def dedupe_solutions(candidates: Iterable[dict]) -> list[dict]:
    """Collapse max-topic ceilings that leave the same clustering, keyed by
    (iteration, sorted topic sizes). The best-ranked duplicate is kept, so
    deduplication can never change which candidate the rule selects."""
    best: dict[tuple, dict] = {}
    for c in candidates:
        if not is_scored(c):
            continue
        key = solution_key(c)
        if outranks(c, best.get(key)):
            best[key] = c
    return sorted(best.values(), key=lambda c: (c.get("iteration", 0), c.get("max_topics", 0)))


def summarize_candidate(candidate: dict | None) -> dict | None:
    if candidate is None:
        return None
    summary = {"iteration": candidate.get("iteration"), "max_topics": candidate.get("max_topics"),
               "n_topics": candidate.get("n_topics_found"), "coherence": candidate.get("coherence"),
               "largest_topic_share_of_assigned": candidate.get("largest_topic_share_of_assigned"),
               "outlier_share": candidate.get("outlier_share")}
    if "topic_diversity_top10" in candidate:  # absent from searches saved before it was recorded
        summary["topic_diversity_top10"] = candidate["topic_diversity_top10"]
    return summary


def _identity(candidate: dict | None) -> tuple | None:
    return None if candidate is None else (candidate.get("iteration"), candidate.get("max_topics"))


def select_candidate(candidates: Iterable[dict], max_topic_share: float | None = 0.5,
                     min_topics: int = 2) -> dict:
    """Apply the declared rule. Returns the admissible winner (``selected``,
    None if nothing is admissible), the unconstrained coherence winner, the
    counts, and a status: ``rule_selected``, ``selection_rule_unmet`` (the
    caller falls back to the unconstrained winner and must say so) or
    ``no_scored_candidates``."""
    validate_rule(max_topic_share, min_topics)
    scored = [c for c in candidates if is_scored(c)]
    admissible = [c for c in scored if is_admissible(c, max_topic_share, min_topics)]
    unconstrained = min(scored, key=rank_key) if scored else None
    selected = min(admissible, key=rank_key) if admissible else None
    status = "rule_selected" if selected else ("selection_rule_unmet" if scored else "no_scored_candidates")
    return {"rule": rule_text(max_topic_share, min_topics), "max_topic_share": max_topic_share,
            "min_topics": min_topics, "status": status, "selected": selected,
            "unconstrained_winner": unconstrained,
            "fallback_to_unconstrained": status == "selection_rule_unmet",
            "rule_changed_selection": bool(selected) and _identity(selected) != _identity(unconstrained),
            "scored_count": len(scored), "admissible_count": len(admissible)}


def _runs(grid: list[dict], field: str, target: tuple | None) -> list[list]:
    """Maximal contiguous runs of grid values at which ``target`` is selected."""
    runs: list[list] = []
    previous = False
    for row in grid:
        hit = target is not None and _identity(row["selected"]) == target
        if hit and previous:
            runs[-1][1] = row[field]
        elif hit:
            runs.append([row[field], row[field]])
        previous = hit
    return runs


def _unchanged_range(grid: list[dict], field: str, default_value, target: tuple | None) -> list | None:
    """The run of grid values containing the default, i.e. where the default winner holds."""
    return next((run for run in _runs(grid, field, target) if run[0] <= default_value <= run[1]), None)


def sensitivity(candidates: Iterable[dict], caps: Sequence[float] = DEFAULT_CAPS,
                mins: Sequence[int] | None = None, max_topic_share: float | None = 0.5,
                min_topics: int = 2) -> dict:
    """Vary one rule parameter at a time, holding the other at its default,
    and the topic floor alone with no cap.

    Reports the winner at every grid value and the contiguous grid range over
    which the default selection is unchanged. Selection is a step function of
    each threshold, so the exact interval is reported too: the cap may range
    from the selected candidate's own largest share up to (not including) the
    smallest largest-share among better-coherence competitors.
    """
    scored = [c for c in candidates if is_scored(c)]
    # No cap behaves exactly like a cap of 1.0: a share of assigned documents never exceeds 1.
    grid_cap = 1.0 if max_topic_share is None else max_topic_share
    caps = sorted(set(caps) | {grid_cap})
    top = max([c.get("n_topics_found") or 0 for c in scored] + [min_topics])
    mins = sorted(set(range(2, top + 1) if mins is None else mins) | {min_topics})
    default = select_candidate(scored, max_topic_share, min_topics)
    target = default["selected"]

    def row(field, value, cap, minimum):
        result = select_candidate(scored, cap, minimum)
        return {field: value, "selected": summarize_candidate(result["selected"]),
                "admissible_count": result["admissible_count"]}

    cap_grid = [row("max_topic_share", cap, cap, min_topics) for cap in caps]
    min_grid = [row("min_topics", m, max_topic_share, m) for m in mins]
    # The topic floor alone (no cap) shows whether either constraint would suffice.
    floor_grid = [row("min_topics", m, None, m) for m in mins]
    exact = None
    if target is not None:
        better = [c for c in scored if rank_key(c) < rank_key(target)]
        cap_rivals = [c["largest_topic_share_of_assigned"] for c in better
                      if (c.get("n_topics_found") or 0) >= min_topics
                      and c.get("largest_topic_share_of_assigned") is not None]

        def floor_interval(cap):
            # Better candidates passing the cap lose only once the floor exceeds their topic count.
            rivals = [c["n_topics_found"] for c in better if is_admissible(c, cap, 1)]
            if is_admissible(target, cap, 1):
                return {"from_inclusive": max(rivals) + 1 if rivals else 1, "to_inclusive": target.get("n_topics_found")}
            return None

        exact = {"max_topic_share": {"from_inclusive": target["largest_topic_share_of_assigned"],
                                     "to_exclusive": min(cap_rivals) if cap_rivals else None,
                                     "note": "to_exclusive null means unchanged up to and including no cap"},
                 "min_topics": floor_interval(max_topic_share),
                 "min_topics_without_cap": floor_interval(None)}
    return {"rule": default["rule"],
            "default": {"max_topic_share": max_topic_share, "min_topics": min_topics,
                        "selected": summarize_candidate(target)},
            "unconstrained_winner": summarize_candidate(default["unconstrained_winner"]),
            "solutions_compared": len(scored),
            "unchanged_grid_range": {
                "max_topic_share": _unchanged_range(cap_grid, "max_topic_share", grid_cap, _identity(target)),
                "min_topics": _unchanged_range(min_grid, "min_topics", min_topics, _identity(target))},
            # Under the floor alone the default need not win at the default floor, so report every run.
            "default_selected_without_cap": {"min_topics": _runs(floor_grid, "min_topics", _identity(target))},
            "unchanged_exact_interval": exact,
            "by_max_topic_share": cap_grid, "by_min_topics": min_grid, "by_min_topics_without_cap": floor_grid}
