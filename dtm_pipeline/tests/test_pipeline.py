"""
Fast checks of pipeline behavior. Run from dtm_pipeline/:

    python -m pytest tests -q

Tests run on isolated fixtures. No API calls
are made.
"""

import math
import os
import sys

import pandas as pd
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
sys.path.insert(0, PKG)

from config import PipelineConfig  # noqa: E402
from llm_backend import ERROR_LABEL, LLMBackend, MockBackend  # noqa: E402
import stage4_classification as s4  # noqa: E402
from stage2_democratic_naming import normalize  # noqa: E402



# --------------------------------------------------------------------------- #
# Stage 4 canonicalization and the Boolean pilot
# --------------------------------------------------------------------------- #

@pytest.fixture
def cfg(tmp_path):
    return PipelineConfig(output_dir=str(tmp_path), max_retries=1, themes=["Delivery", "Community", "Promotions", "Sports", "Gaming"])


@pytest.mark.parametrize("raw, expected", [
    ("Sports", "Sports"),
    ("4. Sports.", "Sports"),
    ('"Community"', "Community"),
    ("Theme: Gaming", "Gaming"),
    ("2", "Community"),
    ("6. The text does not fit into any of these themes.",
     "The text does not fit into any of these themes"),
])
def test_canonicalize_matches(cfg, raw, expected):
    assert s4.canonicalize(raw, cfg) == (expected, "matched")


def test_canonicalize_unmatched_and_error_are_distinguished(cfg):
    assert s4.canonicalize("I cannot classify this", cfg) == (s4.INVALID_LABEL, "unmatched")
    # An API failure must never become "does not fit any theme".
    assert s4.canonicalize(ERROR_LABEL, cfg) == (ERROR_LABEL, "error")


def test_boolean_pilot_returns_none_label_without_hits(cfg):
    dicts = {"Sports": {"draft", "league"}, "Gaming": {"twitch", "royale"}}
    assert s4.boolean_classify("happy holidays everyone", dicts, cfg) == cfg.none_label
    assert s4.boolean_classify(float("nan"), dicts, cfg) == cfg.none_label
    assert s4.boolean_classify("watch the royale on twitch", dicts, cfg) == "Gaming"


def test_normalize_folds_quotes_case_and_periods():
    assert normalize('"Virtual Events."') == normalize("virtual events")


def test_score_labels_kappa(cfg):
    h = pd.Series(["Sports", "Gaming", "Sports", cfg.none_label])
    rep = s4.score_labels(h, h, s4.build_option_list(cfg))
    assert rep["agreement"] == 1.0 and rep["cohens_kappa"] == 1.0


# --------------------------------------------------------------------------- #
# Stage 4 corpus classification: errors retried, blanks skipped, resume
# --------------------------------------------------------------------------- #

class FlakyBackend(LLMBackend):
    """Fails on documents containing 'fail' until `heal()` is called."""
    name = "flaky"

    def __init__(self, cfg):
        super().__init__(cfg)
        self.broken, self.calls = True, 0

    def _complete(self, system, user, max_tokens, temperature):
        self.calls += 1
        if self.broken and "fail" in user:
            raise ConnectionError("simulated outage")
        return "Sports"


def test_classify_corpus_retries_errors_and_resumes(cfg, tmp_path, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    corpus = pd.DataFrame({"tweet": ["draft night", "this will fail", None, "league"]})
    backend = FlakyBackend(cfg)
    first = s4.classify_corpus(backend, corpus, str(tmp_path), cfg)
    assert list(first["status"]) == ["matched", "error", "empty", "matched"]
    assert first.loc[1, "theme"] == ERROR_LABEL
    assert first.loc[2, "theme"] == s4.INVALID_LABEL        # blank: no API call

    backend.broken, backend.calls = False, 0
    second = s4.classify_corpus(backend, corpus, str(tmp_path), cfg)
    assert backend.calls == 1                              # only the failed doc re-tried
    assert list(second["status"]) == ["matched", "matched", "empty", "matched"]


def test_mock_backend_answers_with_an_option(cfg):
    mock = MockBackend(cfg)
    raw = s4.classify_once(mock, "Community community activities tonight", cfg)
    assert s4.canonicalize(raw, cfg)[0] == "Community"


# --------------------------------------------------------------------------- #
# Demonstration corpus

def test_inference_counts_and_increase_positive_direction(tmp_path):
    from stage5_inference import run_stage5
    rows=[{'tweet':str(i),'date':'2019-01-01' if i<10 else '2020-01-01','theme':'A' if i<2 or 10<=i<16 else 'Other','status':'matched'} for i in range(20)]
    (tmp_path/'stage4').mkdir()
    pd.DataFrame(rows).to_csv(tmp_path/'stage4/classified_corpus.csv',index=False)
    cfg=PipelineConfig(output_dir=str(tmp_path),themes=['A'],none_label='Other',periods={'before':['2019-01-01','2019-12-31'],'after':['2020-01-01','2020-12-31']})
    run_stage5(cfg)
    result=pd.read_csv(tmp_path/'stage5/ztest_results.csv').iloc[0]
    assert result.k_a==2 and result.n_a==10 and result.k_b==6 and result.n_b==10
    assert math.isclose(result.percentage_point_change,40) and result.z>0
    assert result.alpha_bonferroni==0.05
