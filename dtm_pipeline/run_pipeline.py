"""
run_pipeline.py — Orchestrate the five-stage pipeline.

Usage:
    python run_pipeline.py --stages 1          # discovery only (no API cost)
    python run_pipeline.py --stages 1,2,3      # through the human worksheet
    python run_pipeline.py --stages 4,5        # after Stage 3 consensus
    python run_pipeline.py --stages all

Stage 3 consensus is a human step: between stages 3 and 4, complete
theme_map_TEMPLATE.csv -> theme_map.csv and set `themes` in config.py.
Stages 2 and 4 call the OpenAI API and require OPENAI_API_KEY.
"""

import argparse
import os
import sys

from config import CONFIG


def main() -> None:
    parser = argparse.ArgumentParser(description="Democratic topic modeling pipeline")
    parser.add_argument("--stages", default="all",
                        help="comma-separated stage numbers (e.g. 1,2,3) or 'all'")
    parser.add_argument("--input", default=None, help="override input CSV path")
    args = parser.parse_args()

    if args.input:
        CONFIG.input_csv = args.input

    stages = ([1, 2, 3, 4, 5] if args.stages.strip().lower() == "all"
              else sorted(int(s) for s in args.stages.split(",")))

    if any(s in stages for s in (2, 4)) and not os.environ.get("OPENAI_API_KEY"):
        sys.exit("OPENAI_API_KEY is not set — required for stages 2 and 4.")

    print(f"Running stages {stages} on {CONFIG.input_csv} "
          f"(outputs -> {CONFIG.output_dir}/)\n")

    if 1 in stages:
        from stage1_topic_discovery import run_stage1
        run_stage1(CONFIG)
    if 2 in stages:
        from stage2_democratic_naming import run_stage2
        run_stage2(CONFIG)
    if 3 in stages:
        from stage3_synthesis_worksheet import run_stage3
        run_stage3(CONFIG)
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
