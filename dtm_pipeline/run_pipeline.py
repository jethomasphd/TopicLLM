"""
run_pipeline.py — Orchestrate the five-stage pipeline.

Usage:
    python run_pipeline.py --stages 1          # discovery only (no API cost)
    python run_pipeline.py --stages 1,2,3      # through the human worksheet
    python run_pipeline.py --stages 4,5        # after Stage 3 consensus
    python run_pipeline.py --stages all

Defaults use original Study 1 data: a 704-text discovery subset and a separate
5,871-nonempty-text analysis corpus. The full release retains all 5,872 records.
Use --profile quickcheck for offline data integrity, or --profile study1-demo
for discovery. Synthetic profiles are explicit legacy software fixtures only.

Stage 3 consensus is a human step: between stages 3 and 4, complete
theme_map_TEMPLATE.csv -> theme_map.csv and set `themes` in config.py.
Stages 2 and 4 call the OpenAI API and require OPENAI_API_KEY, unless
--mock-llm is given (a keyless dry run whose outputs are labeled MOCK).
"""

import argparse
import os
import sys
import json
from pathlib import Path
from dataclasses import fields

if __package__:
    from .config import CONFIG
else:
    from config import CONFIG

if __package__:
    from .config import DEMO_DIR
else:
    from config import DEMO_DIR

GROUND_TRUTH = os.path.join(DEMO_DIR, "demonstration_ground_truth.csv")


def write_ground_truth_classification() -> None:
    """Reference run: give Stage 5 the demonstration corpus's ground-truth
    themes in place of a classifier's output. Because the corpus is
    calibrated to the published demonstration, this returns matching rounded
    prevalence percentages. The z statistics are synthetic calculations,
    not recovered historical estimates."""
    import pandas as pd
    import hashlib
    import json
    from pathlib import Path
    canonical = Path(DEMO_DIR) / "demonstration_corpus.csv"
    if Path(CONFIG.input_csv).read_bytes() != canonical.read_bytes():
        raise ValueError("--ground-truth requires the exact bundled synthetic corpus. Labels cannot be transferred to another dataset.")
    corpus = pd.read_csv(CONFIG.input_csv)
    truth = pd.read_csv(GROUND_TRUTH)[["post_id", "theme"]]
    out = os.path.join(CONFIG.output_dir, "stage4")
    os.makedirs(out, exist_ok=True)
    merged = corpus.merge(truth, on="post_id", how="left", validate="one_to_one")
    if merged['theme'].isna().any():
        raise ValueError("Synthetic truth does not cover every corpus post.")
    merged.assign(status="ground_truth", classifier="ground_truth").to_csv(
        os.path.join(out, "classified_corpus.csv"), index=False)
    Path(out, 'ground_truth_manifest.json').write_text(json.dumps({
        'mode':'synthetic-generator-truth',
        'corpus_sha256':hashlib.sha256(canonical.read_bytes()).hexdigest(),
        'truth_sha256':hashlib.sha256(Path(GROUND_TRUTH).read_bytes()).hexdigest(),
        'human_validation':False,
    }, indent=2), encoding='utf-8')
    print(f"[ground-truth] Wrote ground-truth themes for {len(merged):,} posts to {out}/")


def main() -> None:
    parser = argparse.ArgumentParser(description="Democratic topic modeling pipeline")
    parser.add_argument('--profile',choices=['study1-demo','research','quickcheck','synthetic-e2e','synthetic-quickcheck'],default='study1-demo')
    parser.add_argument('--discovery',choices=['full','reuse'],default='full',help='synthetic-e2e: run full discovery or use verified existing Stage 1 artifacts')
    parser.add_argument('--config',help='JSON object of PipelineConfig fields; no executable configuration')
    parser.add_argument('--backend',choices=['openai','mock','gateway'])
    parser.add_argument('--budget-usd',type=float,help='Explicit total paid-call ceiling, including previous attempts in this output directory')
    parser.add_argument('--max-api-calls',type=int,help='Total attempted-call ceiling across stages and resume')
    parser.add_argument('--plan',action='store_true',help='Print planned stages and worst-case call count without executing')
    parser.add_argument('--record-review',action='store_true',help='Record actual researcher approval of the completed theme map')
    parser.add_argument('--reviewers',nargs='+',help='Names of the actual researchers who completed the review')
    parser.add_argument("--stages", default="all",
                        help="comma-separated stage numbers (e.g. 1,2,3) or 'all'")
    parser.add_argument("--input", default=None, help="override input CSV path")
    parser.add_argument("--discovery-input", default=None, help="Separate discovery CSV; --input alone uses that corpus for discovery too")
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
    if args.profile in ('synthetic-e2e','synthetic-quickcheck'):
        if __package__:
            from .config import synthetic_fixture_config
        else:
            from config import synthetic_fixture_config
        fixture=synthetic_fixture_config()
        for key in ('input_csv','discovery_input_csv','benchmark_csv','stopwords_file'):setattr(CONFIG,key,getattr(fixture,key))
    if args.config:
        if __package__:
            from .config import PipelineConfig
        else:
            from config import PipelineConfig
        values=json.loads(Path(args.config).read_text(encoding='utf-8'))
        allowed={f.name for f in fields(PipelineConfig)}
        if not isinstance(values,dict) or set(values)-allowed: parser.error('Configuration must contain only PipelineConfig fields.')
        for key,value in values.items():setattr(CONFIG,key,value)
        if 'input_csv' in values and 'discovery_input_csv' not in values: CONFIG.discovery_input_csv=None

    if args.input and args.discovery_input is None: CONFIG.discovery_input_csv=None
    for flag, attr in (("input", "input_csv"), ("discovery_input", "discovery_input_csv"), ("benchmark", "benchmark_csv"),
                       ("stopwords", "stopwords_file"),
                       ("output_dir", "output_dir"), ("iterations", "search_iterations"),
                       ("seed", "random_seed"), ("votes", "votes_per_topic"),
                       ("workers", "classify_workers"),("budget_usd","api_budget_usd"),
                       ("max_api_calls","max_api_calls"),("backend","llm_backend")):
        if getattr(args, flag) is not None:
            setattr(CONFIG, attr, getattr(args, flag))
    if args.mock_llm:
        CONFIG.llm_backend = "mock"
    CONFIG.run_mode='synthetic-e2e' if args.profile=='synthetic-e2e' else 'research'
    if any(value<1 for value in [CONFIG.search_iterations,CONFIG.votes_per_topic,CONFIG.classify_workers,CONFIG.max_api_calls]):parser.error('Iterations, votes, workers and call limit must be positive.')
    if args.record_review:
        if __package__:
            from .review import record_human_review
        else:
            from review import record_human_review
        record_human_review(CONFIG,args.reviewers or [])
        print('Recorded researcher approval bound to the current evidence.');return
    if args.profile=='study1-demo' and args.stages=='all': args.stages='1'
    if args.plan:
        import csv
        count=lambda path:sum(1 for _ in csv.DictReader(open(path,encoding='utf-8')))
        topics=Path(CONFIG.output_dir)/'stage1/topics_for_naming.csv'
        n_topics=count(topics) if topics.exists() else CONFIG.topic_max
        planned=[] if args.profile=='quickcheck' else [5] if args.profile=='synthetic-quickcheck' else ([1,2,3,4,5] if args.profile=='synthetic-e2e' or args.stages=='all' else [int(s) for s in args.stages.split(',')])
        print(json.dumps({'profile':args.profile,'stages':planned,'discovery_candidates':CONFIG.search_iterations*(CONFIG.topic_max-CONFIG.topic_min+1) if 1 in planned else 0,
              'naming_calls':n_topics*CONFIG.votes_per_topic if 2 in planned else 0,'benchmark_calls':count(CONFIG.benchmark_csv) if 4 in planned else 0,
              'maximum_corpus_calls':count(CONFIG.input_csv) if 4 in planned else 0,'budget_usd':CONFIG.api_budget_usd,'call_ceiling':CONFIG.max_api_calls,
              'discovery_input':CONFIG.discovery_input_csv or CONFIG.input_csv,'analysis_input':CONFIG.input_csv,'note':'Original Study 1 is an illustrative rerun. Research interpretation requires researcher review; synthetic profiles are test fixtures.'},indent=2));return
    if args.profile=='synthetic-quickcheck':
        if __package__:
            from .synthetic_workflow import quickcheck
        else:
            from synthetic_workflow import quickcheck
        quickcheck(CONFIG);print('PASS: 5 themes, 15 comparisons, all calibrated percentages. No API calls.');return
    if args.profile=='quickcheck':
        if __package__:
            from .study1 import quickcheck
        else:
            from study1 import quickcheck
        report=quickcheck(CONFIG)
        print(json.dumps(report,indent=2));return
    requested_stages = [1,2,3,4,5] if args.profile=='synthetic-e2e' or args.stages.strip().lower()=='all' else [int(s) for s in args.stages.split(',')]
    paid = not args.score_archival and any(s in requested_stages for s in (2,4)) and CONFIG.llm_backend in ('openai','gateway')
    if paid:
        if CONFIG.api_budget_usd is None or not 0 < CONFIG.api_budget_usd <= 1000:
            parser.error('Set a positive --budget-usd before beginning a workflow with paid stages.')
        key_name='OPENAI_API_KEY' if CONFIG.llm_backend=='openai' else 'TOPICLLM_RESEARCH_TOKEN'
        if not os.environ.get(key_name):parser.error(f'{key_name} is not configured; set it privately before paid execution.')
    if args.profile=='synthetic-e2e':
        if __package__:
            from .synthetic_workflow import run_synthetic
        else:
            from synthetic_workflow import run_synthetic
        run_synthetic(CONFIG,discovery=args.discovery);return

    if args.score_archival:
        if __package__:
            from .stage4_classification import score_only
        else:
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
        if __package__:
            from .stage1_topic_discovery import run_stage1
        else:
            from stage1_topic_discovery import run_stage1
        run_stage1(CONFIG)
    if 2 in stages:
        if __package__:
            from .stage2_democratic_naming import run_stage2
        else:
            from stage2_democratic_naming import run_stage2
        run_stage2(CONFIG)
    if 3 in stages:
        if __package__:
            from .stage3_synthesis_worksheet import run_stage3
        else:
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
        if __package__:
            from .stage4_classification import run_stage4
        else:
            from stage4_classification import run_stage4
        run_stage4(CONFIG)
    if 5 in stages:
        if __package__:
            from .stage5_inference import run_stage5
        else:
            from stage5_inference import run_stage5
        run_stage5(CONFIG)

    print("\nPipeline run complete.")


if __name__ == "__main__":
    main()
