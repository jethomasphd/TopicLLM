"""Declared Stage 1 selection rule, own-data columns and --plan estimates.

Pure standard-library paths only: no ML extra, no network, no API calls.
"""
import builtins
import importlib.util
import json
from pathlib import Path

import pytest

from config import DEMO_DIR, PipelineConfig
from sampling import read_selected
from selection_rule import (dedupe_solutions, select_candidate, sensitivity, topic_diversity,
                            validate_rule)

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "examples/sample-reviews.csv"


def candidate(iteration, max_topics, coherence, n_topics, largest, status="scored"):
    sizes = {str(i): 1 for i in range(n_topics)}  # distinct solutions differ in topic count here
    return {"iteration": iteration, "max_topics": max_topics, "status": status, "coherence": coherence,
            "n_topics_found": n_topics, "largest_topic_share_of_assigned": largest, "topic_sizes": sizes,
            "outlier_share": 0.1}


DEGENERATE = candidate(1, 3, 0.61, 2, 0.995)      # the tutorial's failure mode
FEW = candidate(2, 4, 0.58, 3, 0.45)
BALANCED = candidate(3, 13, 0.54, 12, 0.337)
POOL = [DEGENERATE, FEW, BALANCED, candidate(4, 6, None, 0, None, status="insufficient_topics")]


def test_rule_prefers_admissible_candidate_over_degenerate_coherence_winner():
    result = select_candidate(POOL)
    assert result["status"] == "rule_selected"
    assert result["unconstrained_winner"] is DEGENERATE
    assert result["selected"] is FEW
    assert result["rule_changed_selection"] and not result["fallback_to_unconstrained"]
    assert result["scored_count"] == 3 and result["admissible_count"] == 2


def test_min_topics_floor_and_disabled_cap():
    assert select_candidate(POOL, min_topics=4)["selected"] is BALANCED
    uncapped = select_candidate(POOL, max_topic_share=None)
    assert uncapped["selected"] is DEGENERATE and not uncapped["rule_changed_selection"]
    assert select_candidate(POOL, max_topic_share=None, min_topics=3)["selected"] is FEW


def test_no_admissible_candidate_falls_back_with_explicit_status():
    result = select_candidate([DEGENERATE], max_topic_share=0.5)
    assert result["status"] == "selection_rule_unmet"
    assert result["selected"] is None and result["fallback_to_unconstrained"]
    assert result["unconstrained_winner"] is DEGENERATE
    assert select_candidate([])["status"] == "no_scored_candidates"


def test_ties_are_deterministic_and_dedupe_keeps_the_winner():
    early, late = candidate(2, 9, 0.5, 5, 0.3), candidate(7, 5, 0.5, 4, 0.3)
    same_solution = {**candidate(2, 8, 0.5, 5, 0.3)}
    assert select_candidate([late, early, same_solution])["selected"] is same_solution  # earliest iteration, smallest ceiling
    unique = dedupe_solutions([late, early, same_solution])
    assert len(unique) == 2 and same_solution in unique and early not in unique


@pytest.mark.parametrize("cap, floor", [(0, 2), (1.5, 2), (0.5, 0), (True, 2), (0.5, 2.5)])
def test_invalid_rule_parameters_are_rejected(cap, floor):
    with pytest.raises(ValueError):
        validate_rule(cap, floor)


def test_sensitivity_reports_grid_and_exact_unchanged_ranges():
    report = sensitivity(POOL)
    assert report["default"]["selected"]["iteration"] == FEW["iteration"]
    assert report["unchanged_grid_range"]["max_topic_share"] == [0.45, 0.95]
    exact = report["unchanged_exact_interval"]
    assert exact["max_topic_share"] == {"from_inclusive": 0.45, "to_exclusive": 0.995,
                                        "note": "to_exclusive null means unchanged up to and including no cap"}
    assert exact["min_topics"] == {"from_inclusive": 1, "to_inclusive": 3}
    assert exact["min_topics_without_cap"] == {"from_inclusive": 3, "to_inclusive": 3}
    assert report["unchanged_grid_range"]["min_topics"] == [2, 3]
    assert report["default_selected_without_cap"]["min_topics"] == [[3, 3]]
    by_floor = {row["min_topics"]: row["selected"]["iteration"] for row in report["by_min_topics"]}
    assert by_floor[4] == BALANCED["iteration"]


def test_topic_diversity_counts_unique_top_words():
    assert topic_diversity([["a", "b"], ["b", "c"]]) == 0.75
    assert topic_diversity([list("abcdefghijkl")], top_n=10) == 1.0
    assert topic_diversity([]) is None


def test_retrospective_reproduces_the_recorded_tutorial_choice():
    script = ROOT / "scripts/apply-selection-rule.py"
    spec = importlib.util.spec_from_file_location("apply_selection_rule", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    report = module.retrospective(module.TUTORIAL_RESULTS)
    assert report["selected"]["iteration"] == 10 and report["selected"]["max_topics"] == 13
    assert report["selected"]["n_topics"] == 12
    assert report["unconstrained_winner"]["n_topics"] == 2
    assert report["unconstrained_winner"]["largest_topic_share_of_assigned"] > 0.99
    assert report["scored_candidates"] == 1155 and report["unique_solutions"] == 894
    cap = report["sensitivity"]["unchanged_exact_interval"]["max_topic_share"]
    assert cap["from_inclusive"] <= 0.34 and cap["to_exclusive"] > 0.98
    floor = report["sensitivity"]["unchanged_exact_interval"]["min_topics_without_cap"]
    assert floor == {"from_inclusive": 4, "to_inclusive": 12}
    assert report["matches_researcher_selection"] and report["disclosure"].startswith("Formalized after")


# --------------------------------------------------------------------------- #
# Own-data columns

def test_configured_columns_map_onto_internal_names(tmp_path):
    path = tmp_path / "reviews.csv"
    path.write_text("id,text,rating\nx1,Sturdy and quiet,5\nx2,Arrived late,2\n", encoding="utf-8")
    rows, report = read_selected(PipelineConfig(input_csv=str(path), text_column="text", id_column="id"), "discovery")
    assert [(r["post_id"], r["tweet"]) for r in rows] == [("x1", "Sturdy and quiet"), ("x2", "Arrived late")]
    assert "text" not in rows[0] and "id" not in rows[0] and rows[0]["rating"] == "5"
    assert report["selected_records"] == 2


def test_missing_configured_columns_explain_the_setting(tmp_path):
    path = tmp_path / "reviews.csv"
    path.write_text("id,body\nx1,Sturdy\n", encoding="utf-8")
    with pytest.raises(ValueError) as error:
        read_selected(PipelineConfig(input_csv=str(path), text_column="text", id_column="id"), "discovery")
    assert ("reviews.csv needs a 'text' column (set \"text_column\" in your config to the column "
            "holding your documents).") in str(error.value)
    with pytest.raises(ValueError, match="needs an 'uid' column"):
        read_selected(PipelineConfig(input_csv=str(path), text_column="body", id_column="uid"), "discovery")
    path.write_text("text,tweet\nnew,old\n", encoding="utf-8")
    with pytest.raises(ValueError, match="both 'text' and 'tweet'"):
        read_selected(PipelineConfig(input_csv=str(path), text_column="text"), "discovery")


def test_example_config_fields_and_sample_load():
    values = json.loads((ROOT / "examples/your-data-config.json").read_text(encoding="utf-8"))
    cfg = PipelineConfig(**{**values, "input_csv": str(SAMPLE)})
    rows, _ = read_selected(cfg, "discovery")
    assert len(rows) == 40 and len({r["post_id"] for r in rows}) == 40


# --------------------------------------------------------------------------- #
# CLI: plan, warnings, configuration export, missing ML extra

def own_data_config(tmp_path, **overrides):
    values = dict(input_csv=str(SAMPLE), text_column="text", id_column="id", stopwords_file=None,
                  output_dir=str(tmp_path), votes_per_topic=200)
    return PipelineConfig(**{**values, **overrides})


def test_plan_estimates_cost_and_warns_above_call_ceiling(tmp_path):
    import run_pipeline
    plan = run_pipeline.plan_run(own_data_config(tmp_path, max_api_calls=100), "research", [1, 2, 3, 4, 5])
    assert plan["naming_calls"] == 25 * 200 and plan["planned_paid_calls"] == 5000
    assert plan["estimated_usd"]["label"] == "rough estimate"
    assert plan["estimated_usd"]["naming"] == pytest.approx(5000 * (80 * 2.5 + 12 * 10) / 1e6)
    assert plan["estimated_usd"]["total"] == plan["estimated_usd"]["naming"]
    assert plan["estimated_usd"]["classification_if_target_scaled"] > 0
    assert any("exceed max_api_calls (100)" in w for w in plan["warnings"])
    roomy = run_pipeline.plan_run(own_data_config(tmp_path, api_budget_usd=50), "research", [1, 2, 3, 4, 5])
    assert roomy["warnings"] == []


def test_classification_estimate_matches_recorded_tutorial_scale(tmp_path):
    import run_pipeline
    from sampling import CAMPAIGN, PRESIDENCY
    cfg = PipelineConfig(output_dir=str(tmp_path), discovery_window=CAMPAIGN, target_window=PRESIDENCY,
                         require_disjoint_windows=True, stage4_action="classify", max_api_calls=60000,
                         codebook_path=str(ROOT / "docs/data/trump/campaign/codebook.json"))
    plan = run_pipeline.plan_run(cfg, "research", [4])
    assert plan["maximum_corpus_calls"] == 26239
    # Recorded: 1,590 prompt tokens per call; $107.24 for 26,263 attempts.
    assert 1450 < plan["estimate_assumptions"]["classification_tokens_per_call"]["input"] < 1800
    assert 95 < plan["estimated_usd"]["classification"] < 125


def test_trump_stopwords_on_other_corpus_are_named(tmp_path):
    import run_pipeline
    trump_stopwords = str(Path(DEMO_DIR) / "trump/stopwords.txt")
    warning = run_pipeline.bundled_stopwords_warning(own_data_config(tmp_path, stopwords_file=trump_stopwords))
    assert "realdonaldtrump" in warning and '"stopwords_file"' in warning
    assert run_pipeline.bundled_stopwords_warning(PipelineConfig()) is None
    assert run_pipeline.bundled_stopwords_warning(own_data_config(tmp_path)) is None


def test_default_profile_does_not_impose_tutorial_windows_on_own_data(tmp_path, monkeypatch, capsys):
    import run_pipeline, sys
    monkeypatch.setattr(run_pipeline, "CONFIG", own_data_config(tmp_path))
    monkeypatch.setattr(sys, "argv", ["topicllm", "--stages", "1", "--plan"])
    run_pipeline.main()
    plan = json.loads(capsys.readouterr().out)
    assert plan["discovery_selection"]["selected_records"] == 40
    assert plan["discovery_selection"]["window_inclusive"] is None


def test_rule_settings_are_exported_and_validated(tmp_path, monkeypatch):
    import run_pipeline, sys
    path = tmp_path / "research.json"
    monkeypatch.setattr(run_pipeline, "CONFIG", PipelineConfig())
    monkeypatch.setattr(sys, "argv", ["topicllm", "--profile", "research", "--write-config", str(path)])
    run_pipeline.main()
    exported = json.loads(path.read_text(encoding="utf-8"))
    assert exported["max_topic_share"] == 0.5 and exported["min_topics"] == 2
    assert exported["text_column"] == "tweet" and exported["id_column"] == "post_id"
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"max_topic_share": 1.5}), encoding="utf-8")
    monkeypatch.setattr(run_pipeline, "CONFIG", PipelineConfig())
    monkeypatch.setattr(sys, "argv", ["topicllm", "--profile", "research", "--config", str(bad), "--plan"])
    with pytest.raises(SystemExit) as error:
        run_pipeline.main()
    assert error.value.code == 2


def test_missing_ml_extra_gives_install_hint_not_traceback(monkeypatch):
    import run_pipeline
    real_import = builtins.__import__

    def missing(module):
        def fake(name, *args, **kwargs):
            if name.endswith("stage1_topic_discovery"):
                raise ModuleNotFoundError(f"No module named '{module}'", name=module)
            return real_import(name, *args, **kwargs)
        return fake
    monkeypatch.setattr(builtins, "__import__", missing("bertopic"))
    with pytest.raises(SystemExit) as error:
        run_pipeline.load_stage1()
    assert error.value.code == run_pipeline.ML_EXTRA_MESSAGE
    assert 'python -m pip install ".[ml]"' in error.value.code
    monkeypatch.setattr(builtins, "__import__", missing("unrelated_dependency"))
    with pytest.raises(ModuleNotFoundError):  # a genuine bug is not disguised as an install hint
        run_pipeline.load_stage1()
