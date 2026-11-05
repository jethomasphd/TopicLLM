"""
stage2_democratic_naming.py — Democratic LLM topic interpretation (Stage 2).

Queries the LLM independently `votes_per_topic` times per topic and adopts the
modal label: topic naming treated as estimation of a distribution's mode, not
one-shot generation. The prompt is verbatim from the paper (section 2.7) with
the domain context injected from config. Written against the current OpenAI
SDK (openai>=1.0); the archival openai==0.27.0 version is Supplementary File S2.

The reference run is 7 topics x 5,000 votes = 35,000 API calls, so ballots
are checkpointed per topic: an interrupted run resumes at the first topic
whose ballots are incomplete.

Requires  : OPENAI_API_KEY in the environment (llm_backend = "openai").
Inputs    : pipeline_output/stage1/topics_for_naming.csv  (topic, words)
Artifacts : pipeline_output/stage2/
              vote_log.csv        (every individual vote — the raw ballots)
              vote_tallies.csv    (per-topic label counts — publish these)
              topic_names.csv     (modal label per topic + vote share)
"""

import os
from collections import Counter

import pandas as pd

from config import CONFIG
from llm_backend import ERROR_LABEL, LLMBackend, make_backend

SYSTEM = "You are an expert at naming topics."


def build_naming_prompt(words: str, cfg=CONFIG) -> str:
    """Verbatim Stage 2 prompt (paper section 2.7)."""
    return (
        f"The following words represent a topic derived from {cfg.domain_context}: "
        f"{words}. "
        f"Please provide a concise, meaningful topic name that clearly summarizes these words. "
    )


def name_once(backend: LLMBackend, words: str, cfg=CONFIG) -> str:
    """One independent naming query. Decoding parameters match the reference
    implementation: temperature 0.5, max_tokens 15, n=1."""
    return backend.complete(SYSTEM, build_naming_prompt(words, cfg),
                            cfg.naming_max_tokens, cfg.naming_temperature, tag="stage2")


def normalize(label: str) -> str:
    """Canonical form for tallying: strip whitespace, wrapping quotes and
    trailing periods, and case-fold, so '"Sports."' and 'sports' are the
    same ballot."""
    return str(label).strip().strip('"\'“”').strip().rstrip(".").lower()


def run_stage2(cfg=CONFIG) -> str:
    """Collect votes for every topic; write ballots, tallies, and winners."""
    stage1_dir = os.path.join(cfg.output_dir, "stage1")
    out = os.path.join(cfg.output_dir, "stage2")
    os.makedirs(out, exist_ok=True)
    ballot_path = os.path.join(out, "vote_log.csv")

    topics = pd.read_csv(os.path.join(stage1_dir, "topics_for_naming.csv"))
    backend = make_backend(cfg)

    print(f"[stage2] Backend={backend.name}  model={backend.model_id}  "
          f"votes/topic={cfg.votes_per_topic}  early_stop={cfg.early_stop}")
    est_calls = len(topics) * cfg.votes_per_topic
    print(f"[stage2] Upper bound: {est_calls:,} API calls "
          f"({len(topics)} topics x {cfg.votes_per_topic:,} votes)")

    # ---- Resume: keep ballots of topics that finished in a previous run ----
    done: dict = {}
    if os.path.exists(ballot_path):
        prev = pd.read_csv(ballot_path)
        if "model" in prev.columns and (prev["model"] != backend.model_id).any():
            raise RuntimeError(f"{ballot_path} holds ballots from another model; "
                               f"move it aside before voting with {backend.model_id}.")
        for t, g in prev.groupby("topic"):
            if g["complete"].all():
                done[t] = g
        if done:
            print(f"[stage2] Resuming: ballots for topics {sorted(done)} already complete.")

    ballots = [g.drop(columns="complete") for g in done.values()]
    for _, row in topics.iterrows():
        topic_id, words = row["topic"], row["words"]
        if topic_id in done:
            continue
        counts: Counter = Counter()
        topic_ballots = []
        print(f"\n[stage2] Topic {topic_id}: [{words}]")

        for v in range(cfg.votes_per_topic):
            label = name_once(backend, words, cfg)
            topic_ballots.append({"topic": topic_id, "vote_index": v + 1,
                                  "label": label, "model": backend.model_id})
            if label != ERROR_LABEL:  # failed calls are logged, never counted
                counts[normalize(label)] += 1

            if (v + 1) % 250 == 0 and counts:
                lead_key, lead_n = counts.most_common(1)[0]
                print(f"[stage2]   {v + 1:>5} votes — leader: '{lead_key}' "
                      f"({lead_n / sum(counts.values()):.1%})")

            # Optional cost control: the paper notes practitioners can tune cost
            # by monitoring modal-label stability as votes accumulate.
            if cfg.early_stop and (v + 1) >= cfg.early_stop_window and counts:
                lead_key, lead_n = counts.most_common(1)[0]
                if lead_n / sum(counts.values()) >= cfg.early_stop_share:
                    print(f"[stage2]   Early stop at {v + 1} votes "
                          f"(leader share {lead_n / sum(counts.values()):.1%} "
                          f">= {cfg.early_stop_share:.0%})")
                    break

        ballots.append(pd.DataFrame(topic_ballots))
        # Checkpoint after every topic: completed topics are never re-voted.
        log = pd.concat(ballots, ignore_index=True).assign(complete=True)
        log.to_csv(ballot_path, index=False)

    log = pd.concat(ballots, ignore_index=True)
    log.assign(complete=True).to_csv(ballot_path, index=False)

    # ---- Tally ---------------------------------------------------------------
    valid = log[log["label"] != ERROR_LABEL].assign(norm=lambda d: d["label"].map(normalize))
    n_err = int((log["label"] == ERROR_LABEL).sum())
    if n_err:
        print(f"[stage2] WARNING: {n_err} failed API calls logged and excluded from tallies.")
    tallies = (valid.groupby(["topic", "norm"]).size().reset_index(name="votes")
               .sort_values(["topic", "votes"], ascending=[True, False]))
    tallies.to_csv(os.path.join(out, "vote_tallies.csv"), index=False)

    winners = []
    for _, row in topics.iterrows():
        t = row["topic"]
        g = valid[valid["topic"] == t]
        if g.empty:
            raise RuntimeError(f"Topic {t} received no valid votes — check the API.")
        counts = g["norm"].value_counts()
        win_key, win_n = counts.index[0], int(counts.iloc[0])
        total = int(counts.sum())
        margin = (win_n - int(counts.iloc[1])) / total if len(counts) > 1 else 1.0
        display = g.loc[g["norm"] == win_key, "label"].iloc[0]  # first-seen form
        winners.append({
            "topic": t, "words": row["words"], "modal_label": display,
            "votes_for_modal": win_n, "total_votes": total,
            "modal_share": round(win_n / total, 4),
            "margin_over_runner_up": round(margin, 4),
            "distinct_labels": int(len(counts)), "model": backend.model_id,
        })
        # A fragmented vote (low modal_share) flags a semantically ambiguous
        # topic that deserves closer human scrutiny in Stage 3.
        print(f"[stage2] Topic {t} WINNER: '{display}' ({win_n}/{total} = {win_n / total:.1%})")

    pd.DataFrame(winners).to_csv(os.path.join(out, "topic_names.csv"), index=False)
    print(f"\n[stage2] DONE — ballots, tallies, and modal labels in {out}/")
    return out


if __name__ == "__main__":
    run_stage2()
