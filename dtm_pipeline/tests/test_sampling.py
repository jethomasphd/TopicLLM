import csv
from pathlib import Path
import pytest
from dtm_pipeline.config import PipelineConfig
from dtm_pipeline.sampling import CAMPAIGN, PRESIDENCY, read_selected


def test_campaign_target_are_exact_disjoint_views():
    cfg = PipelineConfig(discovery_window=CAMPAIGN, target_window=PRESIDENCY,
                         require_disjoint_windows=True)
    campaign, report = read_selected(cfg, "discovery")
    target, target_report = read_selected(cfg, "target")
    assert len(campaign) == 7805
    assert len(target) == 26239
    assert report["source_records"] == target_report["source_records"] == 34416
    assert report["source_sha256"] == target_report["source_sha256"]
    assert not {r["post_id"] for r in campaign} & {r["post_id"] for r in target}
    assert 34416 - len(campaign) - len(target) == 372
    assert min(r["date"] for r in campaign) == CAMPAIGN[0]
    assert max(r["date"] for r in campaign) == CAMPAIGN[1]
    assert min(r["date"] for r in target) == PRESIDENCY[0]
    assert max(r["date"] for r in target) == PRESIDENCY[1]


def test_overlap_is_rejected():
    cfg = PipelineConfig(discovery_window=CAMPAIGN, target_window=["2016-11-08", "2021-01-08"],
                         require_disjoint_windows=True)
    with pytest.raises(ValueError, match="overlap"):
        read_selected(cfg, "discovery")


def test_invalid_date_cannot_silently_escape_window(tmp_path):
    path = tmp_path / "source.csv"
    path.write_text("post_id,tweet,date\na,text,2016-01-01\nb,other,invalid\n", encoding="utf-8")
    cfg = PipelineConfig(input_csv=str(path), discovery_window=CAMPAIGN)
    with pytest.raises(ValueError, match="invalid ISO date"):
        read_selected(cfg, "discovery")


def test_ids_stay_strings_and_duplicates_rejected(tmp_path):
    path = tmp_path / "source.csv"
    path.write_text("post_id,tweet,date\n9007199254740993,text,2016-01-01\n", encoding="utf-8")
    cfg = PipelineConfig(input_csv=str(path), discovery_window=CAMPAIGN)
    assert read_selected(cfg, "discovery")[0][0]["post_id"] == "9007199254740993"
    path.write_text(path.read_text(encoding="utf-8") + "9007199254740993,again,2016-01-02\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unique"):
        read_selected(cfg, "discovery")
