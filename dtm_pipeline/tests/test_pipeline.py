"""
Fast checks of pipeline behavior. Run from dtm_pipeline/:

    python -m pytest tests -q

Tests run on the open demonstration corpus in docs/data/. No API calls
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
    return PipelineConfig(output_dir=str(tmp_path), max_retries=1)


@pytest.mark.parametrize("raw, expected", [
    ("Sports", "Sports"),
    ("4. Sports.", "Sports"),
    ('"Restaurant Support"', "Restaurant Support"),
    ("Theme: Gaming", "Gaming"),
    ("2", "Restaurant Support"),
    ("6. The text does not fit into any of these themes.",
     "The text does not fit into any of these themes"),
])
def test_canonicalize_matches(cfg, raw, expected):
    assert s4.canonicalize(raw, cfg) == (expected, "matched")


def test_canonicalize_unmatched_and_error_are_distinguished(cfg):
    assert s4.canonicalize("I cannot classify this", cfg) == (cfg.none_label, "unmatched")
    # An API failure must never become "does not fit any theme".
    assert s4.canonicalize(ERROR_LABEL, cfg) == (ERROR_LABEL, "error")


def test_boolean_pilot_returns_none_label_without_hits(cfg):
    dicts = {"Sports": {"draft", "league"}, "Gaming": {"twitch", "royale"}}
    assert s4.boolean_classify("happy holidays everyone", dicts, cfg) == cfg.none_label
    assert s4.boolean_classify(float("nan"), dicts, cfg) == cfg.none_label
    assert s4.boolean_classify("watch the royale on twitch", dicts, cfg) == "Gaming"


def test_normalize_folds_quotes_case_and_periods():
    assert normalize('"Virtual Bar Tours."') == normalize("virtual bar tours")


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
    assert first.loc[2, "theme"] == cfg.none_label        # blank: no API call

    backend.broken, backend.calls = False, 0
    second = s4.classify_corpus(backend, corpus, str(tmp_path), cfg)
    assert backend.calls == 1                              # only the failed doc re-tried
    assert list(second["status"]) == ["matched", "matched", "empty", "matched"]


def test_mock_backend_answers_with_an_option(cfg):
    mock = MockBackend(cfg)
    raw = s4.classify_once(mock, "Support your local restaurant workers tonight", cfg)
    assert s4.canonicalize(raw, cfg)[0] == "Restaurant Support"


# --------------------------------------------------------------------------- #
# Demonstration corpus
# --------------------------------------------------------------------------- #

DEMO = os.path.join(PKG, "..", "docs", "data")

# The published demonstration (Thomas, 2025, Study 1; methods preprint
# Table 2): prevalence (%) pre / peri / post, and z for pre-peri,
# peri-post, pre-post.
PUBLISHED = {
    "Alcohol Delivery and Isolation Drinking": ((9.1, 17.4, 11.9), (6.03, -4.13, 2.98)),
    "Restaurant Support": ((1.9, 5.5, 1.7), (4.89, -6.18, -0.50)),
    "Social Media Promotions": ((6.6, 16.5, 10.6), (7.80, -4.62, 4.59)),
    "Sports": ((8.2, 11.4, 8.9), (2.59, -2.17, 0.83)),
    "Gaming": ((1.1, 2.0, 1.6), (1.80, -0.79, 1.40)),
}


def test_demonstration_corpus_is_reproducible(tmp_path):
    """The shipped files are exactly what the seeded generator writes."""
    import make_demo_data
    corpus, bench, truth = make_demo_data.build()
    shipped = pd.read_csv(os.path.join(DEMO, "demonstration_corpus.csv"))
    assert list(shipped["tweet"]) == list(corpus["tweet"])
    assert len(corpus) == 5872 and corpus["tweet"].is_unique
    assert corpus["brand"].nunique() == 11
    assert len(bench) == 250 and set(bench["human_label"]) <= set(s4.build_option_list(PipelineConfig()))
    assert truth["period"].value_counts().to_dict() == {"post": 3106, "pre": 1707, "peri": 806, "between": 253}


def test_ground_truth_reproduces_published_inference(tmp_path):
    """With ground-truth labels, the pipeline's own Stage 5 returns the
    published prevalence table and z statistics."""
    from stage5_inference import run_stage5
    corpus = pd.read_csv(os.path.join(DEMO, "demonstration_corpus.csv"))
    truth = pd.read_csv(os.path.join(DEMO, "demonstration_ground_truth.csv"))
    os.makedirs(tmp_path / "stage4")
    corpus.merge(truth[["post_id", "theme"]], on="post_id").to_csv(
        tmp_path / "stage4" / "classified_corpus.csv", index=False)
    run_stage5(PipelineConfig(output_dir=str(tmp_path)))
    prev = pd.read_csv(tmp_path / "stage5" / "prevalence_by_period.csv").set_index("theme")
    zt = pd.read_csv(tmp_path / "stage5" / "ztest_results.csv")
    order = ["pre vs peri", "peri vs post", "pre vs post"]
    for theme, (pcts, zs) in PUBLISHED.items():
        got = tuple(round(prev.loc[theme, f"{p}_pct"], 1) for p in ("pre", "peri", "post"))
        assert got == pcts, (theme, got)
        for comp, rep in zip(order, zs):
            z = zt[(zt["theme"] == theme) & (zt["comparison"] == comp)]["z"].iloc[0]
            assert math.isclose(z, rep, abs_tol=0.07), (theme, comp, z, rep)
