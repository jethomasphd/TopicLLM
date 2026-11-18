"""
run_pipeline.py — Orchestrate the five-stage pipeline.

Usage:
    python run_pipeline.py --stages 1          # discovery only (no API cost)
    python run_pipeline.py --stages 1,2,3      # through the human worksheet
    python run_pipeline.py --stages 4,5        # after Stage 3 consensus
    python run_pipeline.py --stages all

Defaults use the one Trump account corpus (34,416 posts, 2015-06-16 through
2021-01-08). quickcheck verifies its bytes and counts; trump-demo runs discovery.
No final human taxonomy or independent benchmark is bundled.

Stage 3 consensus is a human step: complete the local theme-review workspace
and import the actual researchers' approval with topicllm-import-synthesis.
The importer writes the theme map, frozen codebook and JSON configuration.
Stage 4 runs development, held-out validation and accepted scaling separately.
Stages 2 and 4 call the OpenAI API and require OPENAI_API_KEY, unless
--mock-llm is given (a keyless dry run whose outputs are labeled MOCK).
"""

import argparse
import os
import sys
import json
from pathlib import Path
from dataclasses import asdict, fields

if __package__:
    from .config import CONFIG
else:
    from config import CONFIG

if __package__:
    from .config import DEMO_DIR
else:
    from config import DEMO_DIR

def main() -> None:
    parser = argparse.ArgumentParser(description="Democratic topic modeling pipeline")
    parser.add_argument('--profile',choices=['trump-demo','research','quickcheck'],default='trump-demo')
    parser.add_argument('--config',help='JSON object of PipelineConfig fields; no executable configuration')
    parser.add_argument('--write-config',metavar='PATH',help='Write the effective configuration as editable JSON and exit without running; refuses to overwrite')
    parser.add_argument('--backend',choices=['openai','mock','gateway'])
    parser.add_argument('--budget-usd',type=float,help='Explicit total paid-call ceiling, including previous attempts in this output directory')
    parser.add_argument('--max-api-calls',type=int,help='Total attempted-call ceiling across stages and resume')
    parser.add_argument('--plan',action='store_true',help='Print planned stages and worst-case call count without executing')
    parser.add_argument('--record-review',action='store_true',help='Record actual researcher approval of the completed theme map')
    parser.add_argument('--record-validation-review',action='store_true',help='Record actual acceptance of held-out classifier performance')
    parser.add_argument('--record-annotations',help='Record actual human review of this annotation CSV')
    parser.add_argument('--stage4-action',choices=['development','validate','classify'],help='Separate research validation phases; default development')
    parser.add_argument('--reviewers',nargs='+',help='Names of the actual researchers who completed the review')
    parser.add_argument("--stages", default="all",
                        help="comma-separated stage numbers (e.g. 1,2,3) or 'all'")
    parser.add_argument("--input", default=None, help="override input CSV path")
    parser.add_argument("--discovery-input", default=None, help="Separate discovery CSV; --input alone uses that corpus for discovery too")
    parser.add_argument("--benchmark", default=None, help="override benchmark CSV path")
    parser.add_argument("--output-dir", default=None, help="override output directory")
    parser.add_argument("--stopwords", default=None, help="override domain stopword file")
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
    values={}
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
    if args.stage4_action: CONFIG.stage4_action=args.stage4_action
    if __package__:
        from .sampling import CAMPAIGN, PRESIDENCY, read_selected, validate_design
    else:
        from sampling import CAMPAIGN, PRESIDENCY, read_selected, validate_design
    if args.profile == 'trump-demo' and not args.input:
        if CONFIG.discovery_window is None: CONFIG.discovery_window=list(CAMPAIGN)
        if CONFIG.target_window is None: CONFIG.target_window=list(PRESIDENCY)
        CONFIG.require_disjoint_windows=True
        CONFIG.save_candidate_evidence=True
        defaults={'domain_context':'Donald Trump account posts during the 2015-2016 presidential campaign, June 16, 2015 through November 8, 2016, including retweets; describe the content neutrally',
                  'votes_per_topic':500,'naming_max_tokens':32,'naming_workers':12}
        for key,value in defaults.items():
            if key not in values and not (key=='votes_per_topic' and args.votes is not None):setattr(CONFIG,key,value)
    validate_design(CONFIG)
    if args.mock_llm:
        CONFIG.llm_backend = "mock"
    CONFIG.run_mode='research'
    if any(value<1 for value in [CONFIG.search_iterations,CONFIG.votes_per_topic,CONFIG.classify_workers,CONFIG.max_api_calls]):parser.error('Iterations, votes, workers and call limit must be positive.')
    if args.write_config:
        try:
            with Path(args.write_config).open('x', encoding='utf-8', newline='\n') as handle:
                json.dump(asdict(CONFIG), handle, indent=2, ensure_ascii=False)
                handle.write('\n')
        except FileExistsError:
            parser.error('Configuration already exists; choose a new path or edit the existing file.')
        print(f'Wrote {args.write_config}. Review the settings before running; no analysis or API calls made.')
        return
    if args.record_annotations or args.record_validation_review:
        if __package__:
            from .research_validation import record_annotation_review, record_validation_review
        else:
            from research_validation import record_annotation_review, record_validation_review
        if args.record_annotations: record_annotation_review(args.record_annotations,args.reviewers or [],CONFIG)
        else: record_validation_review(CONFIG,args.reviewers or [])
        print('Recorded actual researcher review.');return
    if args.record_review:
        if __package__:
            from .review import record_human_review
        else:
            from review import record_human_review
        record_human_review(CONFIG,args.reviewers or [])
        print('Recorded researcher approval bound to the current evidence.');return
    if args.profile=='trump-demo' and args.stages=='all': args.stages='1'
    if args.plan:
        import csv
        def count(path):
            if not Path(path).exists(): return None
            with open(path,encoding='utf-8') as handle:return sum(1 for _ in csv.DictReader(handle))
        topics=Path(CONFIG.output_dir)/'stage1/topics_for_naming.csv'
        n_topics=count(topics) if topics.exists() else CONFIG.topic_max
        planned=[] if args.profile=='quickcheck' else ([1,2,3,4,5] if args.stages=='all' else [int(s) for s in args.stages.split(',')])
        discovery=read_selected(CONFIG,'discovery')[1] if 1 in planned else None
        target=read_selected(CONFIG,'target')[1] if 4 in planned else None
        benchmark=count(CONFIG.development_csv if CONFIG.stage4_action=='development' else CONFIG.benchmark_csv) if 4 in planned and CONFIG.stage4_action!='classify' else 0
        print(json.dumps({'profile':args.profile,'stages':planned,'discovery_candidates':CONFIG.search_iterations*(CONFIG.topic_max-CONFIG.topic_min+1) if 1 in planned else 0,
              'naming_calls':n_topics*CONFIG.votes_per_topic if 2 in planned else 0,'benchmark_calls':benchmark,
              'maximum_corpus_calls':target['selected_records'] if target and CONFIG.stage4_action=='classify' else 0,
              'stage4_action':CONFIG.stage4_action,'budget_usd':CONFIG.api_budget_usd,'call_ceiling':CONFIG.max_api_calls,
              'discovery_selection':discovery,'target_selection':target,
              'discovery_input':CONFIG.discovery_input_csv or CONFIG.input_csv,'analysis_input':CONFIG.input_csv,
              'note':'Call counts exclude retries; the call and dollar ceilings include all attempts. Null benchmark count means annotations are not supplied. Development, held-out validation and approved scaling run separately.'},indent=2));return
    if args.profile=='quickcheck':
        if __package__:
            from .trump import quickcheck
        else:
            from dtm_pipeline.trump import quickcheck
        report=quickcheck(CONFIG)
        print(json.dumps(report,indent=2));return
    requested_stages = [1,2,3,4,5] if args.stages.strip().lower()=='all' else [int(s) for s in args.stages.split(',')]
    paid = not args.score_archival and any(s in requested_stages for s in (2,4)) and CONFIG.llm_backend in ('openai','gateway')
    if paid:
        if CONFIG.api_budget_usd is None or not 0 < CONFIG.api_budget_usd <= 1000:
            parser.error('Set a positive --budget-usd before beginning a workflow with paid stages.')
        key_name='OPENAI_API_KEY' if CONFIG.llm_backend=='openai' else 'TOPICLLM_RESEARCH_TOKEN'
        if not os.environ.get(key_name):parser.error(f'{key_name} is not configured; set it privately before paid execution.')
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
    if 4 in stages:
        theme_map = os.path.join(CONFIG.output_dir, "stage3", "theme_map.csv")
        if not os.path.exists(theme_map):
            sys.exit(f"Stage 4 needs {theme_map} — complete the Stage 3 "
                     f"human review workspace and import the approved export "
                     f"with topicllm-import-synthesis first.")
        if __package__:
            from .stage4_classification import run_stage4
        else:
            from stage4_classification import run_stage4
        run_stage4(CONFIG)
    if 5 in stages:
        if 4 in stages and CONFIG.validation_mode=='heldout' and CONFIG.stage4_action!='classify':
            print('Stopped at the research validation gate. Stage 5 requires accepted corpus classification.');return
        if __package__:
            from .stage5_inference import run_stage5
        else:
            from stage5_inference import run_stage5
        run_stage5(CONFIG)

    print("\nPipeline run complete.")


if __name__ == "__main__":
    main()
