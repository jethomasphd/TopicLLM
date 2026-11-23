"""
run_pipeline.py — Orchestrate the five-stage pipeline.

Usage:
    python run_pipeline.py --stages 1          # discovery only (no API cost)
    python run_pipeline.py --stages 1,2,3      # through the human worksheet
    python run_pipeline.py --stages 4,5        # after Stage 3 consensus
    python run_pipeline.py --stages all

Defaults use the one Trump account corpus (34,416 posts, 2015-06-16 through
2021-01-08). quickcheck verifies its bytes and counts; trump-demo runs discovery.
No final human taxonomy or independent benchmark is bundled. For your own
corpus, start from examples/your-data-config.json (text_column, id_column,
stopwords_file) and inspect `--profile research --config ... --plan` first.

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
    from .api_budget import INPUT_USD_PER_MILLION, OUTPUT_USD_PER_MILLION, PRICED_MODEL
    from .selection_rule import validate_rule
else:
    from config import DEMO_DIR
    from api_budget import INPUT_USD_PER_MILLION, OUTPUT_USD_PER_MILLION, PRICED_MODEL
    from selection_rule import validate_rule

# Modules only the optional ML extra provides; a missing one means "install the extra".
ML_MODULES = {"bertopic", "sentence_transformers", "umap", "hdbscan", "gensim", "nltk",
              "sklearn", "matplotlib", "tqdm", "torch", "transformers"}
ML_EXTRA_MESSAGE = ('Topic discovery needs the ML extra: python -m pip install ".[ml]"  '
                    '(installed package: python -m pip install "topicllm-research[ml]")')

# Rough per-call token assumptions for --plan cost estimates (not budget enforcement,
# which ApiBudget does conservatively per request).
NAMING_TOKENS = (80, 12)          # input, output per naming ballot
CLASSIFY_OUTPUT_TOKENS = 10
# The tutorial's frozen codebook serializes to about 530 characters per theme;
# used only before a codebook exists.
CODEBOOK_CHARS_PER_THEME = 530


def load_stage1():
    """Import Stage 1, turning a missing ML dependency into an install hint."""
    try:
        if __package__:
            from .stage1_topic_discovery import run_stage1
        else:
            from stage1_topic_discovery import run_stage1
    except ModuleNotFoundError as exc:
        if (exc.name or "").split(".")[0] in ML_MODULES:
            sys.exit(ML_EXTRA_MESSAGE)
        raise
    return run_stage1


def _same_file(path, reference) -> bool:
    a, b = Path(path), Path(reference)
    if not (a.is_file() and b.is_file()):
        return False
    return a.resolve() == b.resolve() or (a.stat().st_size == b.stat().st_size and a.read_bytes() == b.read_bytes())


def bundled_stopwords_warning(cfg) -> str | None:
    """The Trump stopword list is a modeling decision for that archive only;
    applied silently to another corpus it would shape the topics found."""
    bundled = Path(DEMO_DIR) / "trump"
    if not cfg.stopwords_file or not _same_file(cfg.stopwords_file, bundled / "stopwords.txt"):
        return None
    if _same_file(cfg.discovery_input_csv or cfg.input_csv, bundled / "corpus.csv"):
        return None
    text = Path(cfg.stopwords_file).read_text(encoding="utf-8")
    tokens = [w.strip() for w in text.replace("\n", ",").split(",") if w.strip()]
    return (f"stopwords_file is the bundled Trump list ({', '.join(tokens)}), but the input is not the bundled "
            f"Trump corpus. Set \"stopwords_file\" in your config (or --stopwords) to your own list, "
            f"or null for NLTK English stopwords only.")


def _usd(input_tokens: float, output_tokens: float, calls: int) -> float:
    return round(calls * (input_tokens * INPUT_USD_PER_MILLION + output_tokens * OUTPUT_USD_PER_MILLION) / 1e6, 2)


def plan_run(cfg, profile: str, planned: list[int]) -> dict:
    """Planned stages, worst-case call counts and a rough cost estimate, without executing."""
    import csv
    if __package__:
        from .sampling import read_selected
    else:
        from sampling import read_selected

    def count(path):
        if not Path(path).exists(): return None
        with open(path, encoding='utf-8') as handle: return sum(1 for _ in csv.DictReader(handle))
    topics = Path(cfg.output_dir) / 'stage1/topics_for_naming.csv'
    n_topics = count(topics) if topics.exists() else cfg.topic_max
    discovery = read_selected(cfg, 'discovery')[1] if 1 in planned else None
    target_rows, target = read_selected(cfg, 'target') if 4 in planned else (None, None)
    benchmark = count(cfg.development_csv if cfg.stage4_action == 'development' else cfg.benchmark_csv) \
        if 4 in planned and cfg.stage4_action != 'classify' else 0
    naming_calls = n_topics * cfg.votes_per_topic if 2 in planned else 0
    corpus_calls = target['selected_records'] if target and cfg.stage4_action == 'classify' else 0
    classify_calls = (benchmark or 0) + corpus_calls
    planned_calls = naming_calls + classify_calls

    # Classification prompt ~ serialized codebook + mean document, at ~4 characters per token.
    # Calibration: the recorded tutorial averaged 1,590 prompt tokens per classification call.
    if 4 not in planned:
        codebook_chars, codebook_basis = 0, None
    elif cfg.codebook_path and Path(cfg.codebook_path).is_file():
        codebook = json.loads(Path(cfg.codebook_path).read_text(encoding='utf-8'))
        codebook_chars = len(json.dumps(codebook, ensure_ascii=False, sort_keys=True))
        codebook_basis = f'serialized codebook {cfg.codebook_path}'
    else:
        n_themes = len(cfg.themes) or n_topics
        codebook_chars = CODEBOOK_CHARS_PER_THEME * n_themes
        codebook_basis = (f'no codebook yet: assumed {CODEBOOK_CHARS_PER_THEME} characters x {n_themes} themes'
                          + ('' if cfg.themes else ' (planned topic count as an upper bound)'))
    mean_chars = (sum(len(r['tweet']) for r in target_rows) / len(target_rows)) if target_rows else 0
    classify_input = round((codebook_chars + mean_chars) / 4)
    paid = cfg.llm_backend in ('openai', 'gateway')
    naming_usd = _usd(*NAMING_TOKENS, naming_calls) if paid else 0.0
    classify_usd = _usd(classify_input, CLASSIFY_OUTPUT_TOKENS, classify_calls) if paid else 0.0
    estimate = {'label': 'rough estimate', 'naming': naming_usd, 'classification': classify_usd,
                'total': round(naming_usd + classify_usd, 2),
                # The research default stops before scaling; show what scaling would add.
                'classification_if_target_scaled': (_usd(classify_input, CLASSIFY_OUTPUT_TOKENS, target['selected_records'])
                                                    if paid and target else None)}
    warnings = []
    if 1 in planned and (message := bundled_stopwords_warning(cfg)):
        warnings.append(message)
    if planned_calls > cfg.max_api_calls:
        warnings.append(f'Planned calls ({planned_calls:,}) exceed max_api_calls ({cfg.max_api_calls:,}); execution '
                        f'stops at the ceiling. Raise --max-api-calls or reduce votes or scope before running.')
    if paid and planned_calls and cfg.api_budget_usd is None:
        warnings.append('Paid stages are planned but no budget is set; execution refuses to start without --budget-usd.')
    elif paid and cfg.api_budget_usd is not None and estimate['total'] > cfg.api_budget_usd:
        warnings.append(f"Rough estimated cost (${estimate['total']:,.2f}) exceeds the budget "
                        f"(${cfg.api_budget_usd:,.2f}); execution stops at the budget.")
    return {'profile':profile,'stages':planned,'discovery_candidates':cfg.search_iterations*(cfg.topic_max-cfg.topic_min+1) if 1 in planned else 0,
            'naming_calls':naming_calls,'benchmark_calls':benchmark,
            'maximum_corpus_calls':corpus_calls,'planned_paid_calls':planned_calls if paid else 0,
            'stage4_action':cfg.stage4_action,'budget_usd':cfg.api_budget_usd,'call_ceiling':cfg.max_api_calls,
            'estimated_usd':estimate,
            'estimate_assumptions':{'backend':cfg.llm_backend if paid else f'{cfg.llm_backend} (no paid calls)',
                                    'model_prices':f'{PRICED_MODEL}: ${INPUT_USD_PER_MILLION}/${OUTPUT_USD_PER_MILLION} per million input/output tokens',
                                    'naming_tokens_per_call':{'input':NAMING_TOKENS[0],'output':NAMING_TOKENS[1]},
                                    'classification_tokens_per_call':{'input':classify_input,'output':CLASSIFY_OUTPUT_TOKENS} if codebook_basis else None,
                                    'classification_prompt_basis':f'{codebook_basis} + mean document ({mean_chars:.0f} characters), characters/4' if codebook_basis else 'Stage 4 not planned',
                                    'excludes':'retries and format retries; the enforced ledger reserves conservatively per call'},
            'warnings':warnings,
            'discovery_selection':discovery,'target_selection':target,
            'discovery_input':cfg.discovery_input_csv or cfg.input_csv,'analysis_input':cfg.input_csv,
            'note':'Call counts exclude retries; the call and dollar ceilings include all attempts. Null benchmark count means annotations are not supplied. Development, held-out validation and approved scaling run separately.'}


def main() -> None:
    parser = argparse.ArgumentParser(description="TopicLLM: human-guided topic-to-theme measurement")
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
        from .sampling import CAMPAIGN, PRESIDENCY, validate_design
    else:
        from sampling import CAMPAIGN, PRESIDENCY, validate_design
    # Tutorial windows and naming settings belong to the bundled archive only, never to a researcher's own corpus.
    bundled_input=_same_file(CONFIG.discovery_input_csv or CONFIG.input_csv,Path(DEMO_DIR)/'trump'/'corpus.csv')
    if args.profile == 'trump-demo' and not args.input and bundled_input:
        if CONFIG.discovery_window is None: CONFIG.discovery_window=list(CAMPAIGN)
        if CONFIG.target_window is None: CONFIG.target_window=list(PRESIDENCY)
        CONFIG.require_disjoint_windows=True
        CONFIG.save_candidate_evidence=True
        defaults={'domain_context':'Donald Trump account posts during the 2015-2016 presidential campaign, June 16, 2015 through November 8, 2016, including retweets; describe the content neutrally',
                  'votes_per_topic':500,'naming_max_tokens':32,'naming_workers':12}
        for key,value in defaults.items():
            if key not in values and not (key=='votes_per_topic' and args.votes is not None):setattr(CONFIG,key,value)
    validate_design(CONFIG)
    try:
        validate_rule(CONFIG.max_topic_share, CONFIG.min_topics)
    except ValueError as exc:
        parser.error(str(exc))
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
        planned=[] if args.profile=='quickcheck' else ([1,2,3,4,5] if args.stages=='all' else [int(s) for s in args.stages.split(',')])
        plan=plan_run(CONFIG,args.profile,planned)
        for warning in plan['warnings']: print(f'WARNING: {warning}',file=sys.stderr)
        print(json.dumps(plan,indent=2));return
    if args.profile=='quickcheck':
        if __package__:
            from .trump import quickcheck
        else:
            from dtm_pipeline.trump import quickcheck
        report=quickcheck(CONFIG)
        print(json.dumps(report,indent=2));return
    requested_stages = [1,2,3,4,5] if args.stages.strip().lower()=='all' else [int(s) for s in args.stages.split(',')]
    run_stage1 = load_stage1() if 1 in requested_stages and not args.score_archival else None
    if run_stage1 and (warning := bundled_stopwords_warning(CONFIG)):
        print(f'WARNING: {warning}', file=sys.stderr)
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
