"""
stage2_democratic_naming.py — Democratic LLM topic interpretation (Stage 2).

Queries the LLM independently `votes_per_topic` times per topic and adopts the
modal label: topic naming treated as estimation of a distribution's mode, not
one-shot generation. The prompt is verbatim from the paper (section 2.7) with
the domain context injected from config. Written against the current OpenAI
SDK (openai>=1.0); the archival openai==0.27.0 version is Supplementary File S2.

Requires  : OPENAI_API_KEY in the environment.
Inputs    : pipeline_output/stage1/topics_for_naming.csv  (topic, words)
Artifacts : pipeline_output/stage2/
              vote_log.csv        (every individual vote — the raw ballots)
              vote_tallies.csv    (per-topic label counts — publish these)
              topic_names.csv     (modal label per topic + vote share)
"""

import os
import time
from collections import Counter

import pandas as pd
from openai import OpenAI  # pip install openai>=1.0

from config import CONFIG


def name_once(client: OpenAI, words: str, cfg=CONFIG) -> str:
    """One independent naming query. Decoding parameters match the reference
    implementation: temperature 0.5, max_tokens 15, n=1. Retries with
    exponential backoff up to cfg.max_retries."""
    prompt = (
        f"The following words represent a topic derived from {cfg.domain_context}: "
        f"{words}. "
        f"Please provide a concise, meaningful topic name that clearly summarizes these words. "
    )
    for attempt in range(cfg.max_retries):
        try:
            resp = client.chat.completions.create(
                model=cfg.llm_model,
                messages=[
                    {"role": "system", "content": "You are an expert at naming topics."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=cfg.naming_max_tokens,
                temperature=cfg.naming_temperature,
                n=1,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            wait = 2 ** (attempt + 1)
            print(f"[stage2]   API error ({e}); retry {attempt + 1}/{cfg.max_retries} in {wait}s")
            time.sleep(wait)
    return "Error: Unable to generate topic name"


def normalize(label: str) -> str:
    """Canonical form for tallying: strip whitespace/trailing periods and
    case-fold, so 'Sports.' and 'sports' are the same ballot."""
    return label.strip().rstrip(".").lower()


def run_stage2(cfg=CONFIG) -> str:
    """Collect votes for every topic; write ballots, tallies, and winners."""
    stage1_dir = os.path.join(cfg.output_dir, "stage1")
    out = os.path.join(cfg.output_dir, "stage2")
    os.makedirs(out, exist_ok=True)

    topics = pd.read_csv(os.path.join(stage1_dir, "topics_for_naming.csv"))
    client = OpenAI()  # reads OPENAI_API_KEY from the environment

    print(f"[stage2] Model={cfg.llm_model}  votes/topic={cfg.votes_per_topic}  "
          f"early_stop={cfg.early_stop}")
    est_calls = len(topics) * cfg.votes_per_topic
    print(f"[stage2] Upper bound: {est_calls:,} API calls "
          f"({len(topics)} topics x {cfg.votes_per_topic:,} votes)")

    ballots, winners = [], []
    for _, row in topics.iterrows():
        topic_id, words = row["topic"], row["words"]
        counts: Counter = Counter()
        canonical_display: dict[str, str] = {}  # normalized -> first-seen display form
        print(f"\n[stage2] Topic {topic_id}: [{words}]")

        for v in range(cfg.votes_per_topic):
            label = name_once(client, words, cfg)
            key = normalize(label)
            canonical_display.setdefault(key, label)
            counts[key] += 1
            ballots.append({"topic": topic_id, "vote_index": v + 1, "label": label})

            if (v + 1) % 250 == 0:
                lead_key, lead_n = counts.most_common(1)[0]
                print(f"[stage2]   {v + 1:>5} votes — leader: "
                      f"'{canonical_display[lead_key]}' ({lead_n / (v + 1):.1%})")

            # Optional cost control: the paper notes practitioners can tune cost
            # by monitoring modal-label stability as votes accumulate.
            if cfg.early_stop and (v + 1) >= cfg.early_stop_window:
                lead_key, lead_n = counts.most_common(1)[0]
                if lead_n / (v + 1) >= cfg.early_stop_share:
                    print(f"[stage2]   Early stop at {v + 1} votes "
                          f"(leader share {lead_n / (v + 1):.1%} >= {cfg.early_stop_share:.0%})")
                    break

        total = sum(counts.values())
        win_key, win_n = counts.most_common(1)[0]
        runner = counts.most_common(2)
        margin = (win_n - runner[1][1]) / total if len(runner) > 1 else 1.0
        winners.append({
            "topic": topic_id,
            "words": words,
            "modal_label": canonical_display[win_key],
            "votes_for_modal": win_n,
            "total_votes": total,
            "modal_share": round(win_n / total, 4),
            "margin_over_runner_up": round(margin, 4),
        })
        # A fragmented vote (low modal_share) flags a semantically ambiguous
        # topic that deserves closer human scrutiny in Stage 3.
        print(f"[stage2]   WINNER: '{canonical_display[win_key]}' "
              f"({win_n}/{total} = {win_n / total:.1%})")

    pd.DataFrame(ballots).to_csv(os.path.join(out, "vote_log.csv"), index=False)
    tallies = (pd.DataFrame(ballots).assign(norm=lambda d: d["label"].map(normalize))
               .groupby(["topic", "norm"]).size().reset_index(name="votes")
               .sort_values(["topic", "votes"], ascending=[True, False]))
    tallies.to_csv(os.path.join(out, "vote_tallies.csv"), index=False)
    pd.DataFrame(winners).to_csv(os.path.join(out, "topic_names.csv"), index=False)
    print(f"\n[stage2] DONE — ballots, tallies, and modal labels in {out}/")
    return out


if __name__ == "__main__":
    run_stage2()
