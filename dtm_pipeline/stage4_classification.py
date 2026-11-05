"""
stage4_classification.py — Validated corpus-scale classification (Stage 4).

Every document receives exactly one label from the theme taxonomy (or "not
belonging to any theme"). Two candidate classifiers are piloted against a
human-labeled benchmark (n=250 in the reference implementation) and the
better one is scaled — the pipeline REFUSES to scale below the agreement
threshold. The LLM prompt is verbatim from the paper (section 2.7), built
dynamically from the consensus themes in config. Written against the current
OpenAI SDK; the archival version is Supplementary File S3.

Real-corpus safeguards (Study 2 classified 486,786 tweets):
  * failed API calls are recorded as __API_ERROR__, never folded into the
    "does not fit" option, and are re-tried on the next run;
  * every raw model response is kept next to its canonical label, and
    responses that match no option are counted and reported;
  * corpus classification checkpoints every `checkpoint_every` documents and
    resumes after an interruption; `classify_workers` > 1 runs calls
    concurrently;
  * documents with no text are labeled "does not fit" without an API call.

Requires  : OPENAI_API_KEY in the environment (llm_backend = "openai").
Inputs    : tweet_data.csv; human_labels.csv (columns: tweet, human_label);
            stage1/best_model/topic_words.csv + stage3/theme_map.csv
            (for the Boolean pilot's theme dictionaries)
Artifacts : pipeline_output/stage4/
              benchmark_report.json      (agreement, kappa, per-theme metrics)
              benchmark_predictions.csv  (per-document pilot outputs)
              classified_corpus.csv      (full corpus, winning classifier)

Offline audit of archival pilot labels (no API calls):
    python stage4_classification.py --score-only
scores every `*_label` column in the benchmark file against `human_label`.
"""

import argparse
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from config import CONFIG
from llm_backend import ERROR_LABEL, LLMBackend, make_backend

SYSTEM = "You are an expert at classifying text into themes."


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


def classify_once(backend: LLMBackend, text: str, cfg=CONFIG) -> str:
    """One independent classification call. Decoding parameters match the
    reference implementation: temperature 0.5, max_tokens 30, n=1."""
    return backend.complete(SYSTEM, build_prompt(text, cfg),
                            cfg.classify_max_tokens, cfg.classify_temperature, tag="stage4")


def canonicalize(raw: str, cfg=CONFIG) -> tuple[str, str]:
    """Map a raw model response onto the option list.

    Returns (label, status) with status in {"matched", "unmatched", "error",
    "empty"}. Handles leading numbers, wrapping quotes, trailing periods and
    case. Unmatched responses map to the none label (so every document still
    receives exactly one classification) but are counted in the report;
    API errors keep ERROR_LABEL so they can be re-tried, never silently
    becoming "does not fit"."""
    if raw == ERROR_LABEL:
        return ERROR_LABEL, "error"
    cleaned = re.sub(r"^\s*\d+[.)]\s*", "", str(raw)).strip().strip('"\'“”')
    cleaned = cleaned.strip().rstrip(".").lower()
    options = build_option_list(cfg)
    for opt in options:                      # exact match first
        if cleaned == opt.lower():
            return opt, "matched"
    for opt in options:                      # then containment (e.g. "Theme: Sports")
        if opt.lower() in cleaned:
            return opt, "matched"
    if re.fullmatch(r"\d+", cleaned) and 1 <= int(cleaned) <= len(options):
        return options[int(cleaned) - 1], "matched"   # bare option number
    return cfg.none_label, "unmatched"


def is_blank(text) -> bool:
    return text is None or (isinstance(text, float) and pd.isna(text)) or not str(text).strip()


def classify_text(backend: LLMBackend, text, cfg=CONFIG) -> tuple[str, str, str]:
    """(label, status, raw_response) for one document."""
    if is_blank(text):
        return cfg.none_label, "empty", ""
    raw = classify_once(backend, str(text), cfg)
    label, status = canonicalize(raw, cfg)
    return label, status, raw


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
        theme = str(theme).strip()
        if theme not in cfg.themes:
            raise ValueError(f"theme_map.csv uses '{theme}', which is not in config.themes "
                             f"{cfg.themes} — make the two agree before Stage 4.")
        row = words_df.loc[words_df["Topic"] == r["topic"]]
        if row.empty:
            continue
        toks = re.findall(r"[a-zA-Z]+", str(row.iloc[0][rep_col]).lower())
        dictionaries.setdefault(theme, set()).update(toks)
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


def boolean_classify(text, dictionaries: dict[str, set], cfg=CONFIG) -> str:
    """Score each theme by dictionary-word hits (OR logic, more hits = more
    theme-relevant); require >=2 hits (AND logic) to claim a theme. A
    document with no qualifying theme gets the none label explicitly — never
    the first theme by default (an argmax over all-zero scores)."""
    if is_blank(text):
        return cfg.none_label
    toks = set(re.findall(r"[a-zA-Z]+", str(text).lower()))
    scores = {theme: sum(any(_stem_match(t, w) for w in words) for t in toks)
              for theme, words in dictionaries.items()}
    if not scores:
        return cfg.none_label
    best_theme, best_score = max(scores.items(), key=lambda kv: kv[1])
    return best_theme if best_score >= 2 else cfg.none_label


# --------------------------------------------------------------------------- #
# Benchmark scoring
# --------------------------------------------------------------------------- #

def score_labels(human: pd.Series, pred: pd.Series, labels: list[str]) -> dict:
    """Agreement, Cohen's kappa, per-label precision/recall, and the
    confusion matrix (rows = human, columns = classifier)."""
    h = human.astype(str).str.strip()
    p = pred.astype(str).str.strip()
    n = len(h)
    po = float((h == p).mean())
    hc, pc = h.value_counts(), p.value_counts()
    pe = float(sum(hc.get(k, 0) * pc.get(k, 0) for k in set(hc.index) | set(pc.index)) / n / n)
    kappa = (po - pe) / (1 - pe) if pe < 1 else None
    per_label = {}
    for lab in labels:
        tp = int(((h == lab) & (p == lab)).sum())
        per_label[lab] = {
            "human_n": int((h == lab).sum()), "pred_n": int((p == lab).sum()),
            "precision": round(tp / (p == lab).sum(), 4) if (p == lab).any() else None,
            "recall": round(tp / (h == lab).sum(), 4) if (h == lab).any() else None,
        }
    confusion = pd.crosstab(h, p).reindex(index=labels, columns=labels, fill_value=0)
    return {"agreement": round(po, 4), "cohens_kappa": round(kappa, 4) if kappa is not None else None,
            "per_label": per_label, "confusion": confusion.to_dict(orient="index")}


def score_only(cfg=CONFIG) -> dict:
    """Score every existing `*_label` column against human_label (no API)."""
    bench = pd.read_csv(cfg.benchmark_csv)
    labels = build_option_list(cfg)
    cols = [c for c in bench.columns if c.endswith("_label") and c != "human_label"]
    report = {"n_benchmark": len(bench), "labels": labels, "classifiers": {}}
    for c in cols:
        s = score_labels(bench["human_label"], bench[c], labels)
        report["classifiers"][c] = s
        print(f"[stage4] {c:28s} agreement={s['agreement']:.1%}  kappa={s['cohens_kappa']}")
    out = os.path.join(cfg.output_dir, "stage4")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "archival_benchmark_report.json"), "w") as f:
        json.dump(report, f, indent=2)
    print(f"[stage4] Wrote {out}/archival_benchmark_report.json")
    return report


# --------------------------------------------------------------------------- #
# Corpus classification with checkpoint / resume
# --------------------------------------------------------------------------- #

def classify_corpus(backend: LLMBackend, corpus: pd.DataFrame, out: str, cfg=CONFIG) -> pd.DataFrame:
    ckpt = os.path.join(out, "classified_corpus.partial.csv")
    corpus = corpus.reset_index(drop=True).copy()
    corpus["doc_index"] = corpus.index
    done = pd.DataFrame(columns=["doc_index", "theme", "status", "raw_response"])
    if os.path.exists(ckpt):
        done = pd.read_csv(ckpt, keep_default_na=False)
        done = done[done["status"] != "error"]          # re-try failed calls
        print(f"[stage4] Resuming from checkpoint: {len(done):,} documents already classified.")
    finished = set(done["doc_index"].astype(int))
    todo = [i for i in corpus.index if i not in finished]
    print(f"[stage4] Classifying {len(todo):,} documents "
          f"(workers={cfg.classify_workers}, checkpoint every {cfg.checkpoint_every}) ...")

    def work(i):
        label, status, raw = classify_text(backend, corpus.at[i, "tweet"], cfg)
        return {"doc_index": i, "theme": label, "status": status, "raw_response": raw}

    rows = done.to_dict("records")
    step = max(1, cfg.checkpoint_every)
    with ThreadPoolExecutor(max_workers=max(1, cfg.classify_workers)) as pool:
        for start in range(0, len(todo), step):
            chunk = todo[start:start + step]
            rows.extend(pool.map(work, chunk))
            pd.DataFrame(rows).to_csv(ckpt, index=False)
            print(f"[stage4]   {len(rows):,}/{len(corpus):,} classified (checkpointed)")

    labels = pd.DataFrame(rows).astype({"doc_index": int}).set_index("doc_index").sort_index()
    corpus = corpus.join(labels, on="doc_index").drop(columns="doc_index")
    return corpus


# --------------------------------------------------------------------------- #
# Benchmark then scale
# --------------------------------------------------------------------------- #

def run_stage4(cfg=CONFIG) -> str:
    """Pilot both classifiers on the human benchmark; scale the winner if and
    only if it clears the agreement threshold."""
    out = os.path.join(cfg.output_dir, "stage4")
    os.makedirs(out, exist_ok=True)
    backend = make_backend(cfg)
    labels = build_option_list(cfg)

    # ---- Benchmark ---------------------------------------------------------
    bench = pd.read_csv(cfg.benchmark_csv)
    if not {"tweet", "human_label"} <= set(bench.columns):
        raise ValueError(f"{cfg.benchmark_csv} needs columns: tweet, human_label")
    unknown = set(bench["human_label"].astype(str).str.strip()) - set(labels)
    if unknown:
        raise ValueError(f"Benchmark human_label values {sorted(unknown)} are not in the "
                         f"option list {labels}. Map benchmark codes to theme names first "
                         f"(see docs/data/demonstration_benchmark.csv for the format).")
    print(f"[stage4] Benchmarking against {len(bench)} human-labeled documents "
          f"(backend={backend.name}, model={backend.model_id}) ...")

    dictionaries = build_theme_dictionaries(cfg)
    bench["boolean_pred"] = (bench["tweet"].apply(
        lambda t: boolean_classify(t, dictionaries, cfg)) if dictionaries else None)

    preds = []
    for i, text in enumerate(bench["tweet"], 1):
        preds.append(classify_text(backend, text, cfg))
        if i % 25 == 0:
            print(f"[stage4]   {i}/{len(bench)} benchmark documents classified")
    bench["llm_pred"] = [p[0] for p in preds]
    bench["llm_status"] = [p[1] for p in preds]
    bench["llm_raw_response"] = [p[2] for p in preds]
    n_err = int((bench["llm_status"] == "error").sum())
    if n_err:
        raise RuntimeError(f"{n_err} benchmark calls failed after retries — the agreement "
                           f"estimate would be biased. Fix the API issue and re-run.")

    report = {
        "n_benchmark": len(bench),
        "model": backend.model_id,
        "backend": backend.name,
        "threshold": cfg.agreement_threshold,
        "llm": score_labels(bench["human_label"], bench["llm_pred"], labels),
        "llm_unmatched_responses": int((bench["llm_status"] == "unmatched").sum()),
        "boolean": (score_labels(bench["human_label"], bench["boolean_pred"], labels)
                    if dictionaries else None),
    }
    report["llm_agreement"] = report["llm"]["agreement"]
    report["boolean_agreement"] = report["boolean"]["agreement"] if dictionaries else None
    bench.to_csv(os.path.join(out, "benchmark_predictions.csv"), index=False)
    with open(os.path.join(out, "benchmark_report.json"), "w") as f:
        json.dump(report, f, indent=2)
    print(f"[stage4] LLM agreement     : {report['llm_agreement']:.1%} "
          f"(kappa {report['llm']['cohens_kappa']})")
    if report["boolean_agreement"] is not None:
        print(f"[stage4] Boolean agreement : {report['boolean_agreement']:.1%} "
              f"(kappa {report['boolean']['cohens_kappa']})")

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
    print(f"[stage4] Corpus: {len(corpus):,} documents")
    if winner == "llm":
        corpus = classify_corpus(backend, corpus, out, cfg)
        corpus["classifier"] = f"llm:{backend.model_id}"
    else:
        corpus["theme"] = corpus["tweet"].apply(lambda t: boolean_classify(t, dictionaries, cfg))
        corpus["status"] = "boolean"
        corpus["classifier"] = "boolean"

    status = corpus["status"].value_counts().to_dict()
    print(f"[stage4] Label status: {status}")
    if status.get("error"):
        print(f"[stage4] WARNING: {status['error']} documents still carry {ERROR_LABEL} "
              f"after retries — re-run Stage 4 to retry them before Stage 5.")
    corpus.to_csv(os.path.join(out, "classified_corpus.csv"), index=False)
    print(f"[stage4] DONE — classified corpus and benchmark report in {out}/")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--score-only", action="store_true",
                    help="score existing *_label benchmark columns; no API calls")
    a = ap.parse_args()
    score_only() if a.score_only else run_stage4()
