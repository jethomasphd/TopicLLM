"""
stage4_classification.py — Validated corpus-scale classification (Stage 4).

Every document receives exactly one label from the theme taxonomy (or "not
belonging to any theme"). Two candidate classifiers are piloted against a
human-labeled benchmark (n=250 in the reference implementation) and the
better one is scaled — the pipeline REFUSES to scale below the agreement
threshold. The LLM prompt is verbatim from the paper (section 2.7), built
dynamically from the consensus themes in config. Written against the current
OpenAI SDK; the archival version is Supplementary File S3.

Requires  : OPENAI_API_KEY in the environment.
Inputs    : tweet_data.csv; human_labels.csv (columns: tweet, human_label);
            stage1/best_model/topic_words.csv + stage3/theme_map.csv
            (for the Boolean pilot's theme dictionaries)
Artifacts : pipeline_output/stage4/
              benchmark_report.json      (agreement of both pilots)
              benchmark_predictions.csv  (per-document pilot outputs)
              classified_corpus.csv      (full corpus, winning classifier)
"""

import json
import os
import re
import time

import pandas as pd
from openai import OpenAI  # pip install openai>=1.0

from config import CONFIG


# --------------------------------------------------------------------------- #
# Prompt construction (verbatim structure; themes injected from config)
# --------------------------------------------------------------------------- #

def build_option_list(cfg=CONFIG) -> list[str]:
    """The fixed option list: consensus themes + the none-of-these option."""
    return list(cfg.themes) + [cfg.none_label]


def build_prompt(text: str, cfg=CONFIG) -> str:
    """Reproduces the reference prompt exactly, generalized to N themes:
    numbered options, verbatim-response instruction."""
    options = build_option_list(cfg)
    numbered = ", ".join(f"{i + 1}. {opt}" for i, opt in enumerate(options))
    return (
        f"Classify the following text into one of the following {len(options)} themes: {numbered}."
        f"Text: {text}."
        f"Respond with verbatim classification using only the specified {len(options)} options."
    )


def classify_once(client: OpenAI, text: str, cfg=CONFIG) -> str:
    """One independent classification call. Decoding parameters match the
    reference implementation: temperature 0.5, max_tokens 30, n=1."""
    for attempt in range(cfg.max_retries):
        try:
            resp = client.chat.completions.create(
                model=cfg.llm_model,
                messages=[
                    {"role": "system", "content": "You are an expert at classifying text into themes."},
                    {"role": "user", "content": build_prompt(text, cfg)},
                ],
                max_tokens=cfg.classify_max_tokens,
                temperature=cfg.classify_temperature,
                n=1,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            wait = 2 ** (attempt + 1)
            print(f"[stage4]   API error ({e}); retry {attempt + 1}/{cfg.max_retries} in {wait}s")
            time.sleep(wait)
    return "Error"


def canonicalize(raw: str, cfg=CONFIG) -> str:
    """Map a raw model response onto the option list (handles leading numbers,
    trailing periods, case). Unmatched responses map to the none label so
    every document still receives exactly one classification."""
    cleaned = re.sub(r"^\s*\d+[.)]\s*", "", raw).strip().rstrip(".").lower()
    for opt in build_option_list(cfg):
        if cleaned == opt.lower() or opt.lower() in cleaned:
            return opt
    return cfg.none_label


# --------------------------------------------------------------------------- #
# Pilot A: rule-based Boolean dictionary classifier
# --------------------------------------------------------------------------- #

def build_theme_dictionaries(cfg=CONFIG) -> dict[str, set]:
    """Each theme's dictionary = union of its constituent topics' k
    representative words (paper section 2.5), via stage3/theme_map.csv."""
    s1 = os.path.join(cfg.output_dir, "stage1", "best_model", "topic_words.csv")
    s3 = os.path.join(cfg.output_dir, "stage3", "theme_map.csv")
    if not (os.path.exists(s1) and os.path.exists(s3)):
        print("[stage4] Boolean pilot skipped (needs stage1 topic_words.csv and "
              "stage3 theme_map.csv).")
        return {}
    words_df = pd.read_csv(s1)          # BERTopic get_topic_info(): Topic, Representation, ...
    theme_map = pd.read_csv(s3)         # topic, modal_label, theme
    rep_col = "Representation" if "Representation" in words_df.columns else words_df.columns[-1]
    dictionaries: dict[str, set] = {}
    for _, r in theme_map.iterrows():
        theme = r.get("theme")
        if pd.isna(theme) or not str(theme).strip():
            continue  # unmapped topics (e.g., noise) contribute no dictionary
        row = words_df.loc[words_df["Topic"] == r["topic"]]
        if row.empty:
            continue
        toks = re.findall(r"[a-zA-Z]+", str(row.iloc[0][rep_col]).lower())
        dictionaries.setdefault(str(theme).strip(), set()).update(toks)
    return dictionaries


def _stem_match(token: str, dict_word: str) -> bool:
    """Dictionary terms come from lemmatized topic words while classification
    runs on raw text, so exact matching misses inflections ('delivered' vs
    'delivery'). Match on identity, containment-from-start, or a shared
    5-character prefix for longer words — a light stemmer."""
    if token == dict_word:
        return True
    if len(token) >= 4 and len(dict_word) >= 4 and (
            token.startswith(dict_word) or dict_word.startswith(token)):
        return True
    return len(token) >= 5 and len(dict_word) >= 5 and token[:5] == dict_word[:5]


def boolean_classify(text: str, dictionaries: dict[str, set], cfg=CONFIG) -> str:
    """Score each theme by dictionary-word hits (OR logic, more hits = more
    theme-relevant); require >=2 hits (AND logic) to claim a theme."""
    toks = set(re.findall(r"[a-zA-Z]+", str(text).lower()))
    scores = {theme: sum(any(_stem_match(t, w) for w in words) for t in toks)
              for theme, words in dictionaries.items()}
    if not scores:
        return cfg.none_label
    best_theme, best_score = max(scores.items(), key=lambda kv: kv[1])
    return best_theme if best_score >= 2 else cfg.none_label


# --------------------------------------------------------------------------- #
# Benchmark then scale
# --------------------------------------------------------------------------- #

def run_stage4(cfg=CONFIG) -> str:
    """Pilot both classifiers on the human benchmark; scale the winner if and
    only if it clears the agreement threshold."""
    out = os.path.join(cfg.output_dir, "stage4")
    os.makedirs(out, exist_ok=True)
    client = OpenAI()

    # ---- Benchmark ---------------------------------------------------------
    bench = pd.read_csv(cfg.benchmark_csv)
    if not {"tweet", "human_label"} <= set(bench.columns):
        raise ValueError(f"{cfg.benchmark_csv} needs columns: tweet, human_label")
    print(f"[stage4] Benchmarking against {len(bench)} human-labeled documents ...")

    dictionaries = build_theme_dictionaries(cfg)
    bench["boolean_pred"] = (bench["tweet"].apply(
        lambda t: boolean_classify(t, dictionaries, cfg)) if dictionaries else None)

    llm_preds = []
    for i, text in enumerate(bench["tweet"], 1):
        llm_preds.append(canonicalize(classify_once(client, text, cfg), cfg))
        if i % 25 == 0:
            print(f"[stage4]   {i}/{len(bench)} benchmark documents classified")
    bench["llm_pred"] = llm_preds

    def agreement(col: str) -> float | None:
        if bench[col].isna().all():
            return None
        return float((bench[col].str.lower().str.strip()
                      == bench["human_label"].str.lower().str.strip()).mean())

    report = {
        "n_benchmark": len(bench),
        "llm_agreement": agreement("llm_pred"),
        "boolean_agreement": agreement("boolean_pred"),
        "threshold": cfg.agreement_threshold,
        "model": cfg.llm_model,
    }
    bench.to_csv(os.path.join(out, "benchmark_predictions.csv"), index=False)
    with open(os.path.join(out, "benchmark_report.json"), "w") as f:
        json.dump(report, f, indent=2)
    print(f"[stage4] LLM agreement     : {report['llm_agreement']:.1%}")
    if report["boolean_agreement"] is not None:
        print(f"[stage4] Boolean agreement : {report['boolean_agreement']:.1%}")

    # ---- Gate --------------------------------------------------------------
    candidates = {k: v for k, v in
                  {"llm": report["llm_agreement"],
                   "boolean": report["boolean_agreement"]}.items() if v is not None}
    winner, win_agree = max(candidates.items(), key=lambda kv: kv[1])
    if win_agree < cfg.agreement_threshold:
        raise RuntimeError(
            f"Best classifier ('{winner}', {win_agree:.1%}) is below the "
            f"{cfg.agreement_threshold:.0%} threshold — refine the prompt or "
            f"dictionaries and re-benchmark before scaling.")
    print(f"[stage4] Scaling the '{winner}' classifier ({win_agree:.1%} agreement).")

    # ---- Scale to the full corpus ------------------------------------------
    corpus = pd.read_csv(cfg.input_csv)
    print(f"[stage4] Classifying {len(corpus):,} documents ...")
    if winner == "llm":
        labels = []
        for i, text in enumerate(corpus["tweet"], 1):
            labels.append(canonicalize(classify_once(client, text, cfg), cfg))
            if i % 250 == 0:
                print(f"[stage4]   {i:,}/{len(corpus):,}")
        corpus["theme"] = labels
    else:
        corpus["theme"] = corpus["tweet"].apply(
            lambda t: boolean_classify(t, dictionaries, cfg))

    corpus.to_csv(os.path.join(out, "classified_corpus.csv"), index=False)
    print(f"[stage4] DONE — classified corpus and benchmark report in {out}/")
    return out


if __name__ == "__main__":
    run_stage4()
