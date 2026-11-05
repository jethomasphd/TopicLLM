"""
stage1_topic_discovery.py — Coherence-optimized topic discovery (Stage 1).

Discovers topics with BERTopic under randomized hyperparameter search and
selects the configuration maximizing c_v coherence. The search space,
components, and scoring are those of the archival implementation
(Supplementary File S1). This version adds:

  * a seeded search (hyperparameter draws AND each UMAP fit), so a run can
    be reproduced exactly from config.py;
  * the winning model is the fitted candidate that earned the best score —
    not a fresh, re-randomized refit that may yield different topics;
  * fit-once-then-reduce: each sampled (UMAP, HDBSCAN) configuration is fit
    once and then reduced to every maximum topic solution. With a seeded
    UMAP this yields the same topic assignments as refitting per solution
    (verified on the dissertation corpus) at ~1/24th of the cost. Set
    `refit_per_solution = True` to refit per solution exactly as S1 did;
  * per-candidate audit fields: topics actually found (HDBSCAN often finds
    fewer clusters than the maximum solution) and the outlier share.

Inputs   : tweet_data.csv (column 'tweet'), custom_stopwords.txt
Artifacts: pipeline_output/stage1/
             preprocessed_tweets.csv
             all_iteration_results.json      (full audit trail of the search)
             best_model/                     (topics, assignments, visualizations)
             coherence_curve.png
             topics_for_naming.csv           (input to Stage 2)
"""

import copy
import json
import os
import re
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

from config import CONFIG

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


def build_preprocessor(stopwords_file: str) -> tuple[Callable[[str], str], set]:
    """Return a tweet -> cleaned-string function and the full stopword set.

    The stopword set combines NLTK English stopwords with the analyst's
    domain list — the first, deliberately transparent, modeling decision.
    """
    ensure_nltk_data()

    custom = set()
    if os.path.exists(stopwords_file):
        with open(stopwords_file, "r", encoding="utf-8") as f:
            custom = {w.strip().lower() for w in f.read().split(",") if w.strip()}
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
        text = re.sub(r"[^a-zA-Z]", " ", str(text))
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

    def __call__(self, topic_words: list[list[str]]) -> float:
        # processes=1: Gensim's default forks cpu_count-1 workers per call,
        # each a copy of this process — over 1,200 candidates that exhausts
        # memory on real corpora, and it is no faster at tweet-corpus scale.
        cm = CoherenceModel(topics=topic_words, texts=self.tokenized,
                            dictionary=self.dictionary, coherence="c_v",
                            processes=1)
        return cm.get_coherence()


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
    return {"n_topics_found": int(len(set(topics.tolist()) - {-1})),
            "outlier_share": round(float(np.mean(topics == -1)), 4)}


def evaluate_configuration(docs: list[str], embeddings: np.ndarray,
                           embedder: SentenceTransformer, stop_words: set,
                           umap_params: dict, hdbscan_params: dict,
                           topic_range: range, scorer: CoherenceScorer,
                           seed: int | None, refit_per_solution: bool):
    """Score one sampled (UMAP, HDBSCAN) configuration across all maximum
    topic solutions.

    Returns (results, best_model) where results is a list of dicts
    {max_topics, coherence, n_topics_found, outlier_share} for valid models
    and best_model is the fitted model with the highest coherence."""
    results, best_model, best_c = [], None, -np.inf

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
            return results, None

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
            if len(set(model.topics_)) < 2:
                continue
            tw = topic_words_of(model)
            if len(tw) < 2:
                continue
            coherence = float(scorer(tw))
            info = {"max_topics": n_topics, "coherence": coherence, **summarize(model)}
            results.append(info)
            print(f"[stage1]   max_topics={n_topics:>2}  found={info['n_topics_found']:>2}  "
                  f"outliers={info['outlier_share']:.1%}  coherence={coherence:.4f}")
            if coherence > best_c:
                best_c, best_model = coherence, model
        except Exception as e:
            print(f"[stage1]   max_topics={n_topics:>2}  skipped ({e})")
    return results, best_model


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
    rng = np.random.default_rng(cfg.random_seed)
    umap_seed = cfg.random_seed if cfg.seed_umap else None

    # ---- Load & preprocess -------------------------------------------------
    df = pd.read_csv(cfg.input_csv)
    if "tweet" not in df.columns:
        raise ValueError(f"{cfg.input_csv} must contain a 'tweet' column.")
    preprocess, stop_words = build_preprocessor(cfg.stopwords_file)
    print(f"[stage1] Preprocessing {len(df):,} documents ...")
    df["preprocessed_tweet"] = df["tweet"].apply(preprocess)
    empty = df["preprocessed_tweet"].str.strip() == ""
    if empty.any():
        print(f"[stage1] {int(empty.sum()):,} documents are empty after preprocessing "
              f"(no text, or only stopwords/non-alphabetic characters) and are "
              f"excluded from topic discovery.")
    df = df[~empty].reset_index(drop=True)
    df.to_csv(os.path.join(out, "preprocessed_tweets.csv"), index=False)
    docs = df["preprocessed_tweet"].tolist()
    print(f"[stage1] {len(docs):,} non-empty documents retained.")

    # ---- Embed once, reuse across all candidate models ---------------------
    print(f"[stage1] Embedding with {cfg.embedding_model} (one pass) ...")
    embedder = SentenceTransformer(cfg.embedding_model)
    embeddings = embedder.encode(docs, show_progress_bar=True)
    scorer = CoherenceScorer(docs)

    # ---- Search ------------------------------------------------------------
    topic_range = range(cfg.topic_min, cfg.topic_max + 1)
    n_models = cfg.search_iterations * len(topic_range)
    print(f"[stage1] Random search: {cfg.search_iterations} iterations x "
          f"{len(topic_range)} topic solutions = {n_models:,} candidate models "
          f"(seed={cfg.random_seed}, seed_umap={cfg.seed_umap}, "
          f"refit_per_solution={cfg.refit_per_solution})")

    all_iterations, best, best_model = [], {"max_coherence": -np.inf}, None
    for i in range(cfg.search_iterations):
        umap_cfg = _draw(rng, cfg.umap_space)
        hdb_cfg = _draw(rng, cfg.hdbscan_space)

        print(f"\n[stage1] Iteration {i + 1}/{cfg.search_iterations}")
        print(f"[stage1]   UMAP    : {umap_cfg}")
        print(f"[stage1]   HDBSCAN : {hdb_cfg}")

        details, model = evaluate_configuration(
            docs, embeddings, embedder, stop_words, umap_cfg, hdb_cfg,
            topic_range, scorer, umap_seed, cfg.refit_per_solution)
        if not details:
            print("[stage1]   No valid models in this iteration.")
            continue

        top = max(details, key=lambda d: d["coherence"])
        record = {
            "iteration": i + 1,
            "umap_params": umap_cfg,
            "hdbscan_params": hdb_cfg,
            # [max_topics, coherence] pairs — same shape as archival S1 and
            # the browser app — plus the per-candidate audit details.
            "results": [(d["max_topics"], d["coherence"]) for d in details],
            "details": details,
            "max_coherence": top["coherence"],
            "best_max_topics": top["max_topics"],
            "best_n_topics_found": top["n_topics_found"],
        }
        all_iterations.append(record)
        if record["max_coherence"] > best["max_coherence"]:
            best, best_model = record, model
            print(f"[stage1]   ** New best coherence: {best['max_coherence']:.4f} "
                  f"({top['n_topics_found']} topics) **")

    if not all_iterations:
        raise RuntimeError("No valid models across all iterations — check data/parameters.")

    # Full audit trail: every iteration's parameters and scores
    with open(os.path.join(out, "all_iteration_results.json"), "w") as f:
        json.dump({"seed": cfg.random_seed, "seed_umap": cfg.seed_umap,
                   "refit_per_solution": cfg.refit_per_solution,
                   "n_documents": len(docs), "embedding_model": cfg.embedding_model,
                   "iterations": all_iterations}, f, indent=2)

    # ---- Persist the winning model (the candidate that earned the score) --
    final = best_model
    topics = list(final.topics_)
    print(f"\n[stage1] Best configuration: iteration {best['iteration']}, "
          f"max_topics={best['best_max_topics']}, topics found={best['best_n_topics_found']}, "
          f"coherence={best['max_coherence']:.4f}")

    best_dir = os.path.join(out, "best_model")
    os.makedirs(best_dir, exist_ok=True)
    df["topic"] = topics
    df.to_csv(os.path.join(best_dir, "classified_tweets.csv"), index=False)
    final.get_topic_info().to_csv(os.path.join(best_dir, "topic_words.csv"), index=False)
    with open(os.path.join(best_dir, "parameters.json"), "w") as f:
        json.dump({"iteration": best["iteration"],
                   "umap_params": best["umap_params"],
                   "hdbscan_params": best["hdbscan_params"],
                   "max_topics": int(best["best_max_topics"]),
                   "n_topics": int(best["best_n_topics_found"]),
                   "coherence": best["max_coherence"],
                   "seed": cfg.random_seed, "seed_umap": cfg.seed_umap}, f, indent=2)
    try:  # intertopic distance + similarity matrix for the audit record
        final.visualize_topics().write_html(os.path.join(best_dir, "topic_visualization.html"))
        final.visualize_heatmap().write_html(os.path.join(best_dir, "topic_similarity.html"))
    except Exception as e:
        print(f"[stage1] Visualization skipped: {e}")

    # ---- Coherence curve (paper Figure 1 analogue) -------------------------
    xs, ys = zip(*sorted(best["results"]))
    plt.figure(figsize=(10, 6))
    plt.plot(xs, ys, marker="o")
    plt.xlabel("Maximum topic solution (nr_topics)")
    plt.ylabel("Coherence Score (c_v)")
    plt.title("Topic Coherence Scores (Best Configuration)")
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
    print(f"[stage1] Wrote {len(rows)} topics to topics_for_naming.csv")
    print(f"[stage1] DONE — artifacts in {out}/")
    return out


if __name__ == "__main__":
    run_stage1()
