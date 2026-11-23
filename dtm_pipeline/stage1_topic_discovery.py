"""
stage1_topic_discovery.py — Coherence-optimized topic discovery (Stage 1).

Discovers topics with BERTopic under randomized hyperparameter search and
scores every candidate by c_v coherence. The search space, components, and
scoring are those of the archival implementation (Supplementary File S1).
Selection follows a declared admissibility rule (selection_rule.py): the
highest-coherence candidate with at least `min_topics` topics whose largest
topic holds at most `max_topic_share` of assigned documents. Coherence alone
can reward a few topics dominated by common words (Roberts, Stewart & Tingley
2019); in the recorded Trump tutorial the unconstrained winner put 99.5% of
assigned posts in one of two topics. The unconstrained winner is always
recorded, and the selected solution still goes to researchers for inspection
of original documents. This version adds:

  * a seeded search (hyperparameter draws AND each UMAP fit), so a run can
    be repeated within a fixed, recorded environment;
  * the selected model is the fitted candidate that earned its score — not a
    fresh, re-randomized refit that may yield different topics. Only two
    fitted models are retained during the search: the best admissible
    candidate and the unconstrained coherence winner;
  * fit-once-then-reduce: each sampled (UMAP, HDBSCAN) configuration is fit
    once and then reduced to every maximum topic solution. With a seeded
    UMAP this is intended to avoid redundant fits. Equivalence must be checked
    in the recorded dependency environment; this does not assert historical numerical equivalence. Set
    `refit_per_solution = True` to refit per solution exactly as S1 did;
  * per-candidate audit fields: topics actually found (HDBSCAN often finds
    fewer clusters than the maximum solution), the outlier share, the largest
    topic's share of assigned documents, and top-10 topic diversity (reported
    for inspection only; not used for selection).

If no candidate is admissible, the unconstrained winner is saved with
selection status `selection_rule_unmet` and a warning; researchers then
choose by inspection (topicllm-select-candidate) and record why.

Inputs   : corpus CSV (text_column, id_column; mapped to tweet/post_id), stopwords file
Artifacts: pipeline_output/stage1/
             preprocessed_tweets.csv
             all_iteration_results.json      (full audit trail of the search)
             selection_sensitivity.json      (rule outcome across caps and topic floors)
             best_model/                     (selected topics, assignments, visualizations;
                                              parameters.json carries the selection_rule block)
             coherence_curve.png
             topics_for_naming.csv           (input to Stage 2)
"""

import copy
import json
import os
import re
import hashlib
import html
import gzip
from pathlib import Path
from dataclasses import asdict
from typing import Callable

import matplotlib
matplotlib.use("Agg")  # headless-safe (Colab/servers)
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import nltk
from nltk.corpus import stopwords, wordnet
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize

from bertopic import BERTopic
from bertopic.vectorizers import ClassTfidfTransformer
from gensim.corpora import Dictionary
from gensim.models.coherencemodel import CoherenceModel
from hdbscan import HDBSCAN
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import CountVectorizer
from umap import UMAP

if __package__:
    from .config import CONFIG
else:
    from config import CONFIG
if __package__:
    from .provenance import environment
    from .sampling import read_selected
    from . import selection_rule as rule
else:
    from provenance import environment
    from sampling import read_selected
    import selection_rule as rule

NLTK_PACKAGES = {  # resource path -> downloadable package
    "tokenizers/punkt": "punkt",
    "tokenizers/punkt_tab": "punkt_tab",
    "corpora/stopwords": "stopwords",
    "taggers/averaged_perceptron_tagger": "averaged_perceptron_tagger",
    "taggers/averaged_perceptron_tagger_eng": "averaged_perceptron_tagger_eng",
    "corpora/wordnet": "wordnet",
}


# --------------------------------------------------------------------------- #
# Preprocessing (conventional NLP sequence; see paper section 2.1)
# --------------------------------------------------------------------------- #

def ensure_nltk_data() -> None:
    """Download the NLTK resources preprocessing needs, failing loudly.

    nltk.download() reports failure by returning False rather than raising,
    which previously surfaced much later as an opaque LookupError. Package
    names differ across NLTK releases (punkt vs punkt_tab, ..._eng), so a
    resource only has to be available under one of its names.
    """
    missing = []
    for resource, pkg in NLTK_PACKAGES.items():
        try:
            nltk.data.find(resource)
            continue
        except LookupError:
            pass
        if not nltk.download(pkg, quiet=True):
            missing.append(pkg)
    required = {"stopwords", "wordnet"}
    if required & set(missing) or {"punkt", "punkt_tab"} <= set(missing) or \
            {"averaged_perceptron_tagger", "averaged_perceptron_tagger_eng"} <= set(missing):
        raise RuntimeError(
            f"NLTK data could not be downloaded: {missing}. Behind a proxy, "
            f"newer NLTK refuses proxied downloads unless NLTK_ALLOW_PROXIED_URLOPEN=1 "
            f"is set; otherwise run nltk.download() for these packages manually.")


def build_preprocessor(stopwords_file: str | None, strip_platform_artifacts: bool = False) -> tuple[Callable[[str], str], set]:
    """Return a tweet -> cleaned-string function and the full stopword set.

    The stopword set combines NLTK English stopwords with the analyst's
    domain list — the first, deliberately transparent, modeling decision.
    """
    ensure_nltk_data()

    custom = set()
    if not stopwords_file:
        print("[stage1] No domain stopword file declared — using NLTK English stopwords only.")
    elif os.path.exists(stopwords_file):
        with open(stopwords_file, "r", encoding="utf-8") as f:
            custom = {w.strip().lower() for w in re.split(r"[,\n]", f.read()) if w.strip()}
        print(f"[stage1] Loaded {len(custom)} domain stopwords from {stopwords_file}")
    else:
        print(f"[stage1] WARNING: {stopwords_file} not found — using NLTK stopwords only.")

    nltk_sw = set(stopwords.words("english"))
    stop_words = nltk_sw.union(custom)
    # NLTK's English list has grown across releases (179 words in 3.8, more
    # since), so log the size: it is part of the run's provenance.
    print(f"[stage1] Total stopwords: {len(stop_words)} "
          f"(NLTK {nltk.__version__} English list: {len(nltk_sw)})")

    lemmatizer = WordNetLemmatizer()

    def get_wordnet_pos(word: str) -> str:
        tag = nltk.pos_tag([word])[0][1][0].upper()
        return {"J": wordnet.ADJ, "N": wordnet.NOUN,
                "V": wordnet.VERB, "R": wordnet.ADV}.get(tag, wordnet.NOUN)

    def preprocess(text) -> str:
        # Image/video-only tweets have no text: pandas reads them as NaN, and
        # str(NaN) would otherwise enter the corpus as the token "nan".
        if text is None or (isinstance(text, float) and np.isnan(text)):
            return ""
        text = str(text)
        if strip_platform_artifacts:
            text = html.unescape(text)
            text = re.sub(r"https?://\S+|www\.\S+", " ", text, flags=re.I)
            text = re.sub(r"(?<!\w)@\w+", " ", text)
        text = re.sub(r"[^a-zA-Z]", " ", text)
        text = re.sub(r"\s+", " ", text).strip().lower()
        tokens = word_tokenize(text)
        return " ".join(
            lemmatizer.lemmatize(t, get_wordnet_pos(t))
            for t in tokens if t not in stop_words
        )

    return preprocess, stop_words


# --------------------------------------------------------------------------- #
# Model construction and scoring
# --------------------------------------------------------------------------- #

class CoherenceScorer:
    """c_v coherence (Röder et al., 2015) via Gensim's CoherenceModel.

    Tokenizes the corpus and builds the dictionary once instead of once per
    candidate model (1,200 times in the reference search)."""

    def __init__(self, texts: list[str]):
        self.tokenized = [t.split() for t in texts]
        self.dictionary = Dictionary(self.tokenized)
        self.cache = {}

    def __call__(self, topic_words: list[list[str]]) -> float:
        key = tuple(tuple(words) for words in topic_words)
        if key in self.cache:
            return self.cache[key]
        # processes=1: Gensim's default forks cpu_count-1 workers per call,
        # each a copy of this process — over 1,200 candidates that exhausts
        # memory on real corpora, and it is no faster at tweet-corpus scale.
        cm = CoherenceModel(topics=topic_words, texts=self.tokenized,
                            dictionary=self.dictionary, coherence="c_v",
                            processes=1)
        score = float(cm.get_coherence())
        self.cache[key] = score
        return score


def compute_coherence(topic_words: list[list[str]], texts: list[str]) -> float:
    """One-off c_v coherence (kept for callers outside the search loop)."""
    return CoherenceScorer(texts)(topic_words)


def create_bertopic_model(embedder: SentenceTransformer, stop_words: set,
                          umap_params: dict, hdbscan_params: dict,
                          nr_topics: int | None = None,
                          seed: int | None = None) -> BERTopic:
    """Assemble the five BERTopic components (embedding, UMAP, HDBSCAN,
    c-TF-IDF, topic reduction) for one candidate configuration."""
    return BERTopic(
        nr_topics=nr_topics,
        embedding_model=embedder,
        umap_model=UMAP(**umap_params, random_state=seed),
        hdbscan_model=HDBSCAN(**hdbscan_params),
        vectorizer_model=CountVectorizer(stop_words=list(stop_words)),
        ctfidf_model=ClassTfidfTransformer(),
        verbose=False,
    )


def topic_words_of(model: BERTopic) -> list[list[str]]:
    """Representative words of every non-outlier topic (BERTopic pads short
    topics with empty strings, which c_v cannot score)."""
    ids = sorted(t for t in set(model.topics_) if t != -1)
    words = [[w for w, _ in (model.get_topic(t) or []) if w] for t in ids]
    return [w for w in words if w]


def summarize(model: BERTopic) -> dict:
    topics = np.asarray(model.topics_)
    ids, counts = np.unique(topics[topics != -1], return_counts=True)
    return {"n_topics_found": int(len(set(topics.tolist()) - {-1})),
            "outlier_share": round(float(np.mean(topics == -1)), 4),
            "topic_sizes": {str(t): int(n) for t, n in zip(ids, counts)},
            "smallest_topic_n": int(counts.min()) if len(counts) else 0,
            "largest_topic_share_of_assigned": float(counts.max() / counts.sum()) if len(counts) else None}


def evaluate_configuration(docs: list[str], embeddings: np.ndarray,
                           embedder: SentenceTransformer, stop_words: set,
                           umap_params: dict, hdbscan_params: dict,
                           topic_range: range, scorer: CoherenceScorer,
                           seed: int | None, refit_per_solution: bool,
                           on_scored: Callable[[BERTopic, dict], None] | None = None) -> list[dict]:
    """Score one sampled (UMAP, HDBSCAN) configuration across all maximum
    topic solutions.

    Returns one dict per solution {max_topics, status, coherence,
    n_topics_found, outlier_share, ...}. Each scored model is handed to
    `on_scored(model, info)` (evidence saving, selection tracking) and then
    released, so the caller decides which fitted models to retain."""
    results = []

    base = None
    if not refit_per_solution:
        # One UMAP + HDBSCAN fit; every maximum-topic solution is a reduction
        # of the same clustering.
        try:
            base = create_bertopic_model(embedder, stop_words, umap_params,
                                         hdbscan_params, None, seed)
            base.fit_transform(docs, embeddings=embeddings)
        except Exception as e:
            print(f"[stage1]   configuration failed to fit ({e})")
            return [{"max_topics": n, "status": "failed_fit", "error": str(e), "coherence": None} for n in topic_range]

    for n_topics in topic_range:
        try:
            if refit_per_solution:
                model = create_bertopic_model(embedder, stop_words, umap_params,
                                              hdbscan_params, n_topics, seed)
                model.fit_transform(docs, embeddings=embeddings)
            else:
                # Share (do not copy) the embedding model across candidates.
                model = copy.deepcopy(base, {id(base.embedding_model): base.embedding_model})
                model.reduce_topics(docs, nr_topics=n_topics)
            tw = topic_words_of(model)
            if len(tw) < 2:
                results.append({"max_topics": n_topics, "status": "insufficient_topics", "coherence": None, **summarize(model)})
                continue
            coherence = float(scorer(tw))
            if not np.isfinite(coherence):
                results.append({"max_topics": n_topics, "status": "nonfinite_coherence", "coherence": None, **summarize(model)})
                continue
            info = {"max_topics": n_topics, "status": "scored", "coherence": coherence, **summarize(model),
                    "topic_diversity_top10": rule.topic_diversity(tw, 10)}
            results.append(info)
            print(f"[stage1]   max_topics={n_topics:>2}  found={info['n_topics_found']:>2}  "
                  f"outliers={info['outlier_share']:.1%}  largest={info['largest_topic_share_of_assigned']:.1%}  "
                  f"coherence={coherence:.4f}")
            if on_scored:
                on_scored(model, info)
        except Exception as e:
            results.append({"max_topics": n_topics, "status": "failed", "error": str(e), "coherence": None})
            print(f"[stage1]   max_topics={n_topics:>2}  skipped ({e})")
    return results


class SelectionTracker:
    """Retain only the fitted models the declared rule may need at the end:
    the best admissible candidate and the unconstrained coherence winner
    (often the same object). Comparisons reuse selection_rule's ranking, so
    the retained models always match the post-hoc selection over all scores."""

    def __init__(self, max_topic_share: float | None, min_topics: int):
        rule.validate_rule(max_topic_share, min_topics)
        self.max_topic_share, self.min_topics = max_topic_share, min_topics
        self.admissible: tuple[dict, BERTopic] | None = None
        self.unconstrained: tuple[dict, BERTopic] | None = None

    def offer(self, candidate: dict, model: BERTopic) -> None:
        if rule.outranks(candidate, self.unconstrained and self.unconstrained[0]):
            self.unconstrained = (candidate, model)
        if rule.is_admissible(candidate, self.max_topic_share, self.min_topics) and \
                rule.outranks(candidate, self.admissible and self.admissible[0]):
            self.admissible = (candidate, model)


# --------------------------------------------------------------------------- #
# Randomized search (Bergstra & Bengio, 2012)
# --------------------------------------------------------------------------- #

def _draw(rng: np.random.Generator, space: dict) -> dict:
    """One random draw per hyperparameter, as plain Python scalars."""
    out = {}
    for k, values in space.items():
        v = values[int(rng.integers(len(values)))]
        out[k] = v.item() if hasattr(v, "item") else v
    return out


def run_stage1(cfg=CONFIG) -> str:
    """Execute the full Stage 1 search. Returns the stage output directory."""
    out = os.path.join(cfg.output_dir, "stage1")
    os.makedirs(out, exist_ok=True)
    if Path(out, "run_manifest.json").exists():
        raise ValueError("Stage 1 already has a run manifest. Use a new output directory; do not overwrite research evidence.")
    rule.validate_rule(cfg.max_topic_share, cfg.min_topics)  # fail before the costly embedding pass
    rng = np.random.default_rng(cfg.random_seed)
    umap_seed = cfg.random_seed if cfg.seed_umap else None

    # ---- Load & preprocess -------------------------------------------------
    discovery_path = cfg.discovery_input_csv or cfg.input_csv
    selected, selection = read_selected(cfg, "discovery")
    df = pd.DataFrame(selected)
    preprocess, stop_words = build_preprocessor(cfg.stopwords_file, cfg.strip_platform_artifacts)
    manifest = {
        "input_sha256": hashlib.sha256(Path(discovery_path).read_bytes()).hexdigest(),
        "analysis_corpus_sha256": hashlib.sha256(Path(cfg.input_csv).read_bytes()).hexdigest(),
        "selection": selection,
        "effective_stopwords": sorted(stop_words),
        "config": asdict(cfg), "environment": environment(),
        "mode": "maintained-python-discovery", "status": "started",
    }
    Path(out, "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[stage1] Preprocessing {len(df):,} documents ...")
    df["preprocessed_tweet"] = df["tweet"].apply(preprocess)
    empty = df["preprocessed_tweet"].str.strip() == ""
    manifest.update(input_records=len(df), excluded_empty_after_preprocessing=int(empty.sum()), discovery_records=int((~empty).sum()))
    df[empty].to_csv(os.path.join(out, "excluded_empty.csv"), index=False)
    if empty.any():
        print(f"[stage1] {int(empty.sum()):,} documents are empty after preprocessing "
              f"(no text, or only stopwords/non-alphabetic characters) and are "
              f"excluded from topic discovery.")
    df = df[~empty].reset_index(drop=True)
    df.to_csv(os.path.join(out, "preprocessed_tweets.csv"), index=False)
    docs = df["preprocessed_tweet"].tolist()
    if len(docs) < 10:
        raise ValueError("Discovery requires at least 10 non-empty documents after preprocessing.")
    print(f"[stage1] {len(docs):,} non-empty documents retained.")

    # ---- Embed once, reuse across all candidate models ---------------------
    print(f"[stage1] Embedding with {cfg.embedding_model} (one pass) ...")
    embedder = SentenceTransformer(cfg.embedding_model, revision=cfg.embedding_revision)
    manifest['resolved_embedding_revision'] = getattr(getattr(getattr(embedder[0], 'auto_model', None), 'config', None), '_commit_hash', None)
    embeddings = embedder.encode(docs, show_progress_bar=True)
    if cfg.save_candidate_evidence:
        np.save(Path(out, "embeddings.npy"), embeddings)
        Path(out, "candidates").mkdir(exist_ok=True)
    scorer = CoherenceScorer(docs)

    # ---- Search ------------------------------------------------------------
    topic_range = range(cfg.topic_min, cfg.topic_max + 1)
    n_models = cfg.search_iterations * len(topic_range)
    print(f"[stage1] Random search: {cfg.search_iterations} iterations x "
          f"{len(topic_range)} topic solutions = {n_models:,} candidate models "
          f"(seed={cfg.random_seed}, seed_umap={cfg.seed_umap}, "
          f"refit_per_solution={cfg.refit_per_solution})")

    tracker = SelectionTracker(cfg.max_topic_share, cfg.min_topics)
    all_iterations = []
    for i in range(cfg.search_iterations):
        umap_cfg = _draw(rng, cfg.umap_space)
        hdb_cfg = _draw(rng, cfg.hdbscan_space)

        print(f"\n[stage1] Iteration {i + 1}/{cfg.search_iterations}")
        print(f"[stage1]   UMAP    : {umap_cfg}")
        print(f"[stage1]   HDBSCAN : {hdb_cfg}")

        def on_scored(model, info):
            candidate = {"iteration": i + 1, "umap_params": umap_cfg, "hdbscan_params": hdb_cfg, **info}
            if cfg.save_candidate_evidence:
                evidence = {**candidate,
                            "topics": [{"topic": int(t), "words": [w for w, _ in model.get_topic(t) if w]}
                                       for t in sorted(set(model.topics_)) if t != -1],
                            "assignments": [int(t) for t in model.topics_]}
                # Assignment order is bound to preprocessed_tweets.csv; retain every scored candidate.
                payload = json.dumps(evidence, separators=(",", ":")).encode("utf-8")
                Path(out, "candidates", f"iteration-{i+1:03d}-max-{info['max_topics']:02d}.json.gz").write_bytes(gzip.compress(payload, mtime=0))
            tracker.offer(candidate, model)

        details = evaluate_configuration(
            docs, embeddings, embedder, stop_words, umap_cfg, hdb_cfg,
            topic_range, scorer, umap_seed, cfg.refit_per_solution, on_scored)
        scored = [d for d in details if d["status"] == "scored"]
        top = max(scored, key=lambda d: d["coherence"]) if scored else None
        record = {
            "iteration": i + 1,
            "umap_params": umap_cfg,
            "hdbscan_params": hdb_cfg,
            # [max_topics, coherence] pairs — same shape as archival S1 and
            # the browser app — plus the per-candidate audit details.
            "results": [(d["max_topics"], d["coherence"]) for d in scored],
            "details": details,
            # Unconstrained per-iteration maximum, kept for continuity with S1.
            "max_coherence": top["coherence"] if top else None,
            "best_max_topics": top["max_topics"] if top else None,
            "best_n_topics_found": top["n_topics_found"] if top else None,
        }
        all_iterations.append(record)
        Path(out, "search_progress.json").write_text(json.dumps({"completed_iterations": i + 1, "planned_iterations": cfg.search_iterations, "iterations": all_iterations}, indent=2), encoding="utf-8")
        if tracker.admissible and tracker.admissible[0]["iteration"] == i + 1:
            c = tracker.admissible[0]
            print(f"[stage1]   ** New best admissible candidate: coherence {c['coherence']:.4f} "
                  f"({c['n_topics_found']} topics, largest {c['largest_topic_share_of_assigned']:.1%}) **")

    # Full audit trail: every iteration's parameters and scores
    with open(os.path.join(out, "all_iteration_results.json"), "w") as f:
        json.dump({"seed": cfg.random_seed, "seed_umap": cfg.seed_umap,
                   "refit_per_solution": cfg.refit_per_solution,
                   "n_documents": len(docs), "embedding_model": cfg.embedding_model,
                   "iterations": all_iterations}, f, indent=2)

    if tracker.unconstrained is None:
        raise RuntimeError("No valid models across all iterations — inspect all_iteration_results.json.")

    # ---- Apply the declared rule to every recorded score ---------------------
    candidates = rule.flatten_iterations(all_iterations)
    unique = rule.dedupe_solutions(candidates)
    choice = rule.select_candidate(unique, cfg.max_topic_share, cfg.min_topics)
    tracked = tracker.admissible or tracker.unconstrained
    expected = choice["selected"] or choice["unconstrained_winner"]
    if (tracked[0]["iteration"], tracked[0]["max_topics"]) != (expected["iteration"], expected["max_topics"]):
        raise RuntimeError("Retained model differs from the rule applied to recorded scores; inspect all_iteration_results.json.")
    best, final = tracked
    rule_met = choice["status"] == "rule_selected"
    sensitivity = rule.sensitivity(unique, max_topic_share=cfg.max_topic_share, min_topics=cfg.min_topics)
    sensitivity.update(scored_candidates=sum(rule.is_scored(c) for c in candidates), unique_solutions=len(unique),
                       note="Solutions deduplicated by (iteration, sorted topic sizes).")
    Path(out, "selection_sensitivity.json").write_text(json.dumps(sensitivity, indent=2), encoding="utf-8")
    selection_rule = {
        "rule": choice["rule"], "max_topic_share": cfg.max_topic_share, "min_topics": cfg.min_topics,
        "status": choice["status"],
        "selected": rule.summarize_candidate(best),
        "unconstrained_winner": rule.summarize_candidate(choice["unconstrained_winner"]),
        "rule_changed_selection": choice["rule_changed_selection"],
        "scored_candidates": sensitivity["scored_candidates"], "unique_solutions": len(unique),
        "admissible_count": choice["admissible_count"],
        "admissible_count_basis": "unique solutions",
        "sensitivity": {"file": "selection_sensitivity.json",
                        "unchanged_grid_range": sensitivity["unchanged_grid_range"],
                        "unchanged_exact_interval": sensitivity["unchanged_exact_interval"]},
        "topic_diversity_top10": "reported per candidate for inspection; not used for selection",
    }
    if rule_met:
        print(f"\n[stage1] Selected (declared rule): iteration {best['iteration']}, "
              f"max_topics={best['max_topics']}, topics found={best['n_topics_found']}, "
              f"coherence={best['coherence']:.4f}")
    else:
        selection_rule["fallback"] = "unconstrained coherence winner saved; researcher selection required"
        print(f"\n[stage1] WARNING: no candidate satisfies the declared selection rule ({rule_summary(cfg)}). "
              f"Saving the unconstrained coherence winner with status selection_rule_unmet. Inspect "
              f"candidates and record a researcher selection (topicllm-select-candidate) before naming.")

    # ---- Persist the selected model (the candidate that earned the score) --
    topics = list(final.topics_)
    best_dir = os.path.join(out, "best_model")
    os.makedirs(best_dir, exist_ok=True)
    # Full serialization retains the scored UMAP/HDBSCAN candidate as well as
    # embeddings. Load only your own trusted pickle in this recorded environment.
    model_path = os.path.join(best_dir, 'fitted_model.pkl')
    final.save(model_path, serialization='pickle', save_embedding_model=True)
    manifest['fitted_model_sha256'] = hashlib.sha256(Path(model_path).read_bytes()).hexdigest()
    df["topic"] = topics
    df.to_csv(os.path.join(best_dir, "classified_tweets.csv"), index=False)
    final.get_topic_info().to_csv(os.path.join(best_dir, "topic_words.csv"), index=False)
    with open(os.path.join(best_dir, "parameters.json"), "w") as f:
        json.dump({"iteration": best["iteration"],
                   "umap_params": best["umap_params"],
                   "hdbscan_params": best["hdbscan_params"],
                   "max_topics": int(best["max_topics"]),
                   "n_topics": int(best["n_topics_found"]),
                   "coherence": best["coherence"],
                   "largest_topic_share_of_assigned": best["largest_topic_share_of_assigned"],
                   "seed": cfg.random_seed, "seed_umap": cfg.seed_umap,
                   "selection_status": choice["status"],
                   "selection_rule": selection_rule}, f, indent=2)
    try:  # intertopic distance + similarity matrix for the audit record
        final.visualize_topics().write_html(os.path.join(best_dir, "topic_visualization.html"))
        final.visualize_heatmap().write_html(os.path.join(best_dir, "topic_similarity.html"))
    except Exception as e:
        print(f"[stage1] Visualization skipped: {e}")

    # ---- Coherence curve of the selected configuration (paper Figure 1 analogue)
    selected_record = next(r for r in all_iterations if r["iteration"] == best["iteration"])
    xs, ys = zip(*sorted(selected_record["results"]))
    plt.figure(figsize=(10, 6))
    plt.plot(xs, ys, marker="o")
    plt.axvline(best["max_topics"], color="#176b67", linestyle="--")
    plt.xlabel("Maximum topic solution (nr_topics)")
    plt.ylabel("Coherence Score (c_v)")
    plt.title("Topic Coherence Scores (Selected Configuration)")
    plt.tight_layout()
    plt.savefig(os.path.join(out, "coherence_curve.png"), dpi=200)
    plt.close()

    # ---- Hand-off to Stage 2: one row per topic with representative words --
    rows = []
    for t in sorted(set(topics)):
        if t == -1:  # HDBSCAN noise cluster; not named
            continue
        words = [w for w, _ in final.get_topic(t) if w]
        rows.append({"topic": t, "words": ", ".join(words),
                     "n_documents": int(sum(1 for x in topics if x == t))})
    pd.DataFrame(rows).to_csv(os.path.join(out, "topics_for_naming.csv"), index=False)
    # The search itself completed; the selection status is recorded separately
    # so an unmet rule still allows an explicit researcher selection.
    manifest.update(status="complete", selected_iteration=best["iteration"], selected_max_topics=best["max_topics"],
                    selected_coherence=best["coherence"], selection_status=choice["status"],
                    selection_rule=selection_rule)
    Path(out, "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    unconstrained = choice["unconstrained_winner"]
    print(f"[stage1] Selection rule ({rule_summary(cfg)}): {choice['status']} — "
          f"iteration {best['iteration']}/max {best['max_topics']} ({best['n_topics_found']} topics, "
          f"c_v {best['coherence']:.4f}, largest {best['largest_topic_share_of_assigned']:.1%}); "
          f"unconstrained winner iteration {unconstrained['iteration']}/max {unconstrained['max_topics']} "
          f"({unconstrained['n_topics_found']} topics, c_v {unconstrained['coherence']:.4f}, "
          f"largest {unconstrained['largest_topic_share_of_assigned']:.1%}); "
          f"{choice['admissible_count']}/{len(unique)} unique solutions admissible.")
    print(f"[stage1] Wrote {len(rows)} topics to topics_for_naming.csv")
    print(f"[stage1] DONE — artifacts in {out}/")
    return out


def rule_summary(cfg) -> str:
    cap = "no cap" if cfg.max_topic_share is None else f"largest topic <= {cfg.max_topic_share:.0%} of assigned"
    return f"{cap}, >= {cfg.min_topics} topics"


if __name__ == "__main__":
    run_stage1()
