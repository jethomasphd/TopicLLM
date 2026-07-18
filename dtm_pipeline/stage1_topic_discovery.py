"""
stage1_topic_discovery.py — Coherence-optimized topic discovery (Stage 1).

Discovers topics with BERTopic under randomized hyperparameter search and
selects the configuration maximizing c_v coherence. Logic is identical to the
archival implementation (Supplementary File S1); this version adds a seeded
RNG for a reproducible search, structured artifact output, and progress
reporting suitable for long runs.

Inputs   : tweet_data.csv (column 'tweet'), custom_stopwords.txt
Artifacts: pipeline_output/stage1/
             preprocessed_tweets.csv
             all_iteration_results.json      (full audit trail of the search)
             best_model/                     (topics, assignments, visualizations)
             coherence_curve.png
             topics_for_naming.csv           (input to Stage 2)
"""

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


# --------------------------------------------------------------------------- #
# Preprocessing (conventional NLP sequence; see paper section 2.1)
# --------------------------------------------------------------------------- #

def build_preprocessor(stopwords_file: str) -> tuple[Callable[[str], str], set]:
    """Return a tweet -> cleaned-string function and the full stopword set.

    The stopword set combines NLTK English stopwords with the analyst's
    domain list — the first, deliberately transparent, modeling decision.
    """
    for pkg in ("punkt", "punkt_tab", "stopwords",
                "averaged_perceptron_tagger", "averaged_perceptron_tagger_eng",
                "wordnet"):
        try:
            nltk.download(pkg, quiet=True)
        except Exception:
            pass  # newer/older NLTK versions ship different tagger packages

    custom = set()
    if os.path.exists(stopwords_file):
        with open(stopwords_file, "r", encoding="utf-8") as f:
            custom = {w.strip().lower() for w in f.read().split(",") if w.strip()}
        print(f"[stage1] Loaded {len(custom)} domain stopwords from {stopwords_file}")
    else:
        print(f"[stage1] WARNING: {stopwords_file} not found — using NLTK stopwords only.")

    stop_words = set(stopwords.words("english")).union(custom)
    print(f"[stage1] Total stopwords: {len(stop_words)}")

    lemmatizer = WordNetLemmatizer()

    def get_wordnet_pos(word: str) -> str:
        tag = nltk.pos_tag([word])[0][1][0].upper()
        return {"J": wordnet.ADJ, "N": wordnet.NOUN,
                "V": wordnet.VERB, "R": wordnet.ADV}.get(tag, wordnet.NOUN)

    def preprocess(text: str) -> str:
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

def compute_coherence(topic_words: list[list[str]], texts: list[str]) -> float:
    """c_v coherence (Röder et al., 2015) via Gensim's CoherenceModel."""
    tokenized = [t.split() for t in texts]
    dictionary = Dictionary(tokenized)
    cm = CoherenceModel(topics=topic_words, texts=tokenized,
                        dictionary=dictionary, coherence="c_v")
    return cm.get_coherence()


def create_bertopic_model(embedder: SentenceTransformer, stop_words: set,
                          umap_params: dict, hdbscan_params: dict,
                          nr_topics: int | None = None) -> BERTopic:
    """Assemble the five BERTopic components (embedding, UMAP, HDBSCAN,
    c-TF-IDF, topic reduction) for one candidate configuration."""
    return BERTopic(
        nr_topics=nr_topics,
        embedding_model=embedder,
        umap_model=UMAP(**umap_params),
        hdbscan_model=HDBSCAN(**hdbscan_params),
        vectorizer_model=CountVectorizer(stop_words=list(stop_words)),
        ctfidf_model=ClassTfidfTransformer(),
        verbose=False,
    )


def evaluate_configuration(docs: list[str], embeddings: np.ndarray,
                           embedder: SentenceTransformer, stop_words: set,
                           umap_params: dict, hdbscan_params: dict,
                           topic_range: range) -> list[tuple[int, float]]:
    """Score one sampled (UMAP, HDBSCAN) configuration across all maximum
    topic solutions. Returns [(n_topics, coherence), ...] for valid models."""
    results = []
    for n_topics in topic_range:
        try:
            model = create_bertopic_model(embedder, stop_words,
                                          umap_params, hdbscan_params,
                                          nr_topics=n_topics)
            topics, _ = model.fit_transform(docs, embeddings=embeddings)
            if len(set(topics)) < 2:
                continue
            tw = [[w for w, _ in model.get_topic(t)]
                  for t in range(n_topics) if model.get_topic(t)]
            if len(tw) < 2:
                continue
            coherence = compute_coherence(tw, docs)
            results.append((n_topics, coherence))
            print(f"[stage1]   n_topics={n_topics:>2}  coherence={coherence:.4f}")
        except Exception as e:
            print(f"[stage1]   n_topics={n_topics:>2}  skipped ({e})")
    return results


# --------------------------------------------------------------------------- #
# Randomized search (Bergstra & Bengio, 2012)
# --------------------------------------------------------------------------- #

def run_stage1(cfg=CONFIG) -> str:
    """Execute the full Stage 1 search. Returns the stage output directory."""
    out = os.path.join(cfg.output_dir, "stage1")
    os.makedirs(out, exist_ok=True)
    rng = np.random.default_rng(cfg.random_seed)

    # ---- Load & preprocess -------------------------------------------------
    df = pd.read_csv(cfg.input_csv)
    if "tweet" not in df.columns:
        raise ValueError(f"{cfg.input_csv} must contain a 'tweet' column.")
    preprocess, stop_words = build_preprocessor(cfg.stopwords_file)
    print(f"[stage1] Preprocessing {len(df):,} documents ...")
    df["preprocessed_tweet"] = df["tweet"].apply(preprocess)
    df = df[df["preprocessed_tweet"].str.strip() != ""].reset_index(drop=True)
    df.to_csv(os.path.join(out, "preprocessed_tweets.csv"), index=False)
    docs = df["preprocessed_tweet"].tolist()
    print(f"[stage1] {len(docs):,} non-empty documents retained.")

    # ---- Embed once, reuse across all candidate models ---------------------
    print(f"[stage1] Embedding with {cfg.embedding_model} (one pass) ...")
    embedder = SentenceTransformer(cfg.embedding_model)
    embeddings = embedder.encode(docs, show_progress_bar=True)

    # ---- Search ------------------------------------------------------------
    topic_range = range(cfg.topic_min, cfg.topic_max + 1)
    n_models = cfg.search_iterations * len(topic_range)
    print(f"[stage1] Random search: {cfg.search_iterations} iterations x "
          f"{len(topic_range)} topic solutions = {n_models:,} candidate models "
          f"(seed={cfg.random_seed})")

    all_iterations, best = [], {"max_coherence": -np.inf}
    for i in range(cfg.search_iterations):
        umap_cfg = {k: rng.choice(v).item() if hasattr(rng.choice(v), "item")
                    else rng.choice(v) for k, v in cfg.umap_space.items()}
        hdb_cfg = {k: rng.choice(v).item() if hasattr(rng.choice(v), "item")
                   else rng.choice(v) for k, v in cfg.hdbscan_space.items()}
        # numpy choice on str lists returns np.str_; normalize for JSON/BERTopic
        umap_cfg = {k: (str(v) if isinstance(v, (np.str_,)) else v) for k, v in umap_cfg.items()}
        hdb_cfg = {k: (str(v) if isinstance(v, (np.str_,)) else v) for k, v in hdb_cfg.items()}

        print(f"\n[stage1] Iteration {i + 1}/{cfg.search_iterations}")
        print(f"[stage1]   UMAP    : {umap_cfg}")
        print(f"[stage1]   HDBSCAN : {hdb_cfg}")

        results = evaluate_configuration(docs, embeddings, embedder, stop_words,
                                         umap_cfg, hdb_cfg, topic_range)
        if not results:
            print("[stage1]   No valid models in this iteration.")
            continue

        record = {
            "iteration": i + 1,
            "umap_params": umap_cfg,
            "hdbscan_params": hdb_cfg,
            "results": [(int(n), float(c)) for n, c in results],
            "max_coherence": float(max(c for _, c in results)),
        }
        all_iterations.append(record)
        if record["max_coherence"] > best["max_coherence"]:
            best = record
            print(f"[stage1]   ** New best coherence: {best['max_coherence']:.4f} **")

    if not all_iterations:
        raise RuntimeError("No valid models across all iterations — check data/parameters.")

    # Full audit trail: every iteration's parameters and scores
    with open(os.path.join(out, "all_iteration_results.json"), "w") as f:
        json.dump({"seed": cfg.random_seed, "iterations": all_iterations}, f, indent=2)

    # ---- Refit and persist the winning model -------------------------------
    n_best = max(best["results"], key=lambda x: x[1])[0]
    print(f"\n[stage1] Best configuration: iteration {best['iteration']}, "
          f"n_topics={n_best}, coherence={best['max_coherence']:.4f}")
    final = create_bertopic_model(embedder, stop_words, best["umap_params"],
                                  best["hdbscan_params"], nr_topics=n_best)
    topics, _ = final.fit_transform(docs, embeddings=embeddings)

    best_dir = os.path.join(out, "best_model")
    os.makedirs(best_dir, exist_ok=True)
    df["topic"] = topics
    df.to_csv(os.path.join(best_dir, "classified_tweets.csv"), index=False)
    final.get_topic_info().to_csv(os.path.join(best_dir, "topic_words.csv"), index=False)
    with open(os.path.join(best_dir, "parameters.json"), "w") as f:
        json.dump({"umap_params": best["umap_params"],
                   "hdbscan_params": best["hdbscan_params"],
                   "n_topics": int(n_best),
                   "coherence": best["max_coherence"],
                   "seed": cfg.random_seed}, f, indent=2)
    try:  # intertopic distance + similarity matrix for the audit record
        final.visualize_topics().write_html(os.path.join(best_dir, "topic_visualization.html"))
        final.visualize_heatmap().write_html(os.path.join(best_dir, "topic_similarity.html"))
    except Exception as e:
        print(f"[stage1] Visualization skipped: {e}")

    # ---- Coherence curve (paper Figure 1 analogue) -------------------------
    xs, ys = zip(*sorted(best["results"]))
    plt.figure(figsize=(10, 6))
    plt.plot(xs, ys, marker="o")
    plt.xlabel("Number of Topics")
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
        words = [w for w, _ in final.get_topic(t)]
        rows.append({"topic": t, "words": ", ".join(words)})
    pd.DataFrame(rows).to_csv(os.path.join(out, "topics_for_naming.csv"), index=False)
    print(f"[stage1] Wrote {len(rows)} topics to topics_for_naming.csv")
    print(f"[stage1] DONE — artifacts in {out}/")
    return out


if __name__ == "__main__":
    run_stage1()
