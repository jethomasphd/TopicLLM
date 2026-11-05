"""
run_pipeline.py — Orchestrate the five-stage pipeline.

Usage:
    python run_pipeline.py --stages 1          # discovery only (no API cost)
    python run_pipeline.py --stages 1,2,3      # through the human worksheet
    python run_pipeline.py --stages 4,5        # after Stage 3 consensus
    python run_pipeline.py --stages all

Defaults run on the open demonstration corpus (docs/data/). Without an
API key, the whole pipeline can be exercised end to end:
    python run_pipeline.py --stages 1                  # discovery
    python run_pipeline.py --stages 2,3 --mock-llm     # keyless dry run
    python run_pipeline.py --ground-truth --stages 5   # reference inference

Stage 3 consensus is a human step: between stages 3 and 4, complete
theme_map_TEMPLATE.csv -> theme_map.csv and set `themes` in config.py.
Stages 2 and 4 call the OpenAI API and require OPENAI_API_KEY, unless
--mock-llm is given (a keyless dry run whose outputs are labeled MOCK).
"""

import argparse
import os
import sys

from config import CONFIG

from config import DEMO_DIR

GROUND_TRUTH = os.path.join(DEMO_DIR, "demonstration_ground_truth.csv")


def write_ground_truth_classification() -> None:
    """Reference run: give Stage 5 the demonstration corpus's ground-truth
    themes in place of a classifier's output. Because the corpus is
    calibrated to the published demonstration, this returns the published
    prevalence table and z statistics, which checks the inference code. A
    real classifier's results approach it as its agreement with the ground
    truth rises."""
    import pandas as pd
    corpus = pd.read_csv(CONFIG.input_csv)
    truth = pd.read_csv(GROUND_TRUTH)[["post_id", "theme"]]
    out = os.path.join(CONFIG.output_dir, "stage4")
    os.makedirs(out, exist_ok=True)
    merged = corpus.merge(truth, on="post_id", how="left", validate="one_to_one")
    merged.assign(status="ground_truth", classifier="ground_truth").to_csv(
        os.path.join(out, "classified_corpus.csv"), index=False)
    print(f"[ground-truth] Wrote ground-truth themes for {len(merged):,} posts to {out}/")


def main() -> None:
    parser = argparse.ArgumentParser(description="Democratic topic modeling pipeline")
    parser.add_argument("--stages", default="all",
                        help="comma-separated stage numbers (e.g. 1,2,3) or 'all'")
    parser.add_argument("--input", default=None, help="override input CSV path")
    parser.add_argument("--benchmark", default=None, help="override benchmark CSV path")
    parser.add_argument("--output-dir", default=None, help="override output directory")
    parser.add_argument("--stopwords", default=None, help="override domain stopword file")
    parser.add_argument("--ground-truth", action="store_true",
                        help="demonstration corpus only: feed Stage 5 the ground-truth themes "
                             "instead of a Stage 4 classification (reference run)")
    parser.add_argument("--iterations", type=int, default=None,
                        help="override search_iterations (e.g. 2 for a quick check)")
    parser.add_argument("--seed", type=int, default=None, help="override random_seed")
    parser.add_argument("--votes", type=int, default=None, help="override votes_per_topic")
    parser.add_argument("--workers", type=int, default=None, help="override classify_workers")
    parser.add_argument("--mock-llm", action="store_true",
                        help="keyless dry run of stages 2/4 (outputs are NOT measurements)")
    parser.add_argument("--score-archival", action="store_true",
                        help="score the benchmark's existing *_label columns (no API) and exit")
    args = parser.parse_args()

    for flag, attr in (("input", "input_csv"), ("benchmark", "benchmark_csv"),
                       ("stopwords", "stopwords_file"),
                       ("output_dir", "output_dir"), ("iterations", "search_iterations"),
                       ("seed", "random_seed"), ("votes", "votes_per_topic"),
                       ("workers", "classify_workers")):
        if getattr(args, flag) is not None:
            setattr(CONFIG, attr, getattr(args, flag))
    if args.mock_llm:
        CONFIG.llm_backend = "mock"

    if args.score_archival:
        from stage4_classification import score_only
        score_only(CONFIG)
        return

    stages = ([1, 2, 3, 4, 5] if args.stages.strip().lower() == "all"
              else sorted(int(s) for s in args.stages.split(",")))

    if (any(s in stages for s in (2, 4)) and CONFIG.llm_backend == "openai"
            and not os.environ.get("OPENAI_API_KEY")):
        sys.exit("OPENAI_API_KEY is not set — required for stages 2 and 4 "
                 "(or pass --mock-llm for a keyless dry run).")

    print(f"Running stages {stages} on {CONFIG.input_csv} "
          f"(outputs -> {CONFIG.output_dir}/, LLM backend: {CONFIG.llm_backend})\n")

    if 1 in stages:
        from stage1_topic_discovery import run_stage1
        run_stage1(CONFIG)
    if 2 in stages:
        from stage2_democratic_naming import run_stage2
        run_stage2(CONFIG)
    if 3 in stages:
        from stage3_synthesis_worksheet import run_stage3
        run_stage3(CONFIG)
    if args.ground_truth:
        if 4 in stages:
            sys.exit("--ground-truth replaces Stage 4; run it with --stages 5.")
        write_ground_truth_classification()
    if 4 in stages:
        theme_map = os.path.join(CONFIG.output_dir, "stage3", "theme_map.csv")
        if not os.path.exists(theme_map):
            sys.exit(f"Stage 4 needs {theme_map} — complete the Stage 3 "
                     f"consensus (fill theme_map_TEMPLATE.csv, save as "
                     f"theme_map.csv, update config.themes) first.")
        from stage4_classification import run_stage4
        run_stage4(CONFIG)
    if 5 in stages:
        from stage5_inference import run_stage5
        run_stage5(CONFIG)

    print("\nPipeline run complete.")


if __name__ == "__main__":
    main()
