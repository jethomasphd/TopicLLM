"""Explicit synthetic acceptance workflows, distinct from researcher approval."""
import json
import platform
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import asdict
import pandas as pd
if __package__:
    from .config import DEMO_DIR, PipelineConfig
else:
    from config import DEMO_DIR, PipelineConfig
if __package__:
    from .review import exact_synthetic_inputs, synthetic_review, sha
else:
    from review import exact_synthetic_inputs, synthetic_review, sha
if __package__:
    from .provenance import checkpoint_guard, environment
else:
    from provenance import checkpoint_guard, environment


def quickcheck(cfg):
    """Generator-truth inference only: fast, offline and explicit about its scope."""
    exact_synthetic_inputs(cfg)
    if __package__:
        from .stage5_inference import run_stage5
    else:
        from stage5_inference import run_stage5
    corpus=pd.read_csv(cfg.input_csv)
    truth=pd.read_csv(Path(DEMO_DIR)/'demonstration_ground_truth.csv')[['post_id','theme']]
    result=corpus.merge(truth,on='post_id',validate='one_to_one')
    out=Path(cfg.output_dir)/'stage4'; out.mkdir(parents=True,exist_ok=True)
    result.assign(status='ground_truth',classifier='synthetic-generator-truth').to_csv(out/'classified_corpus.csv',index=False)
    (out/'ground_truth_manifest.json').write_text(json.dumps({'mode':'synthetic-generator-truth','human_validation':False,'corpus_sha256':sha(cfg.input_csv)},indent=2),encoding='utf-8')
    run_stage5(cfg)
    return validate_outputs(cfg,truth_expected=True)


def validate_outputs(cfg, truth_expected=False):
    root=Path(cfg.output_dir)
    corpus=pd.read_csv(cfg.input_csv)
    classified=pd.read_csv(root/'stage4/classified_corpus.csv')
    if len(classified)!=len(corpus) or classified.post_id.tolist()!=corpus.post_id.tolist():
        raise AssertionError('Classification must preserve every input ID and its order.')
    if not set(classified.theme)<=set(cfg.themes+[cfg.none_label]): raise AssertionError('Unresolved classification')
    # Inspect the actual stage artifact names, not an assumed historical report.
    prevalence=pd.read_csv(root/'stage5/prevalence_by_period.csv')
    tests=pd.read_csv(root/'stage5/ztest_results.csv')
    if len(prevalence)!=5 or len(tests)!=15: raise AssertionError('Expected five themes and fifteen comparisons.')
    study=json.loads((Path(DEMO_DIR)/'study.json').read_text(encoding='utf-8'))
    matches=[]
    for row in prevalence.to_dict('records'):
        target=next(t for t in study['prevalence'] if t['theme']==row['theme'])
        for period in cfg.periods:
            matches.append({'theme':row['theme'],'period':period,'computed':round(float(row[f'{period}_pct']),1),'reported':target[period]})
    if truth_expected and any(r['computed']!=r['reported'] for r in matches): raise AssertionError('Synthetic calibration mismatch')
    report={'status':'passed','mode':'synthetic-generator-truth' if truth_expected else 'synthetic-live-predictions',
            'records':len(classified),'theme_rows':len(prevalence),'comparisons':len(tests),'prevalence_comparison':matches,
            'human_validation':False,'historical_recomputation':False,'environment':environment()}
    (root/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


def run_synthetic(cfg, discovery='full'):
    exact_synthetic_inputs(cfg)
    cfg.run_mode='synthetic-e2e'
    root=Path(cfg.output_dir); root.mkdir(parents=True,exist_ok=True)
    spec=asdict(cfg); spec.pop('api_budget_usd'); spec.pop('max_api_calls')
    checkpoint_guard(root/'synthetic_run_identity.json',spec)
    state={'status':'running','mode':'synthetic-e2e','human_review_performed':False,'started_at':datetime.now(timezone.utc).isoformat(),'configuration':asdict(cfg),'stages':{}}
    def save(): (root/'synthetic_run.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
    save()
    try:
        if discovery=='full':
            if __package__:
                from .stage1_topic_discovery import run_stage1
            else:
                from stage1_topic_discovery import run_stage1
            run_stage1(cfg)
        elif discovery!='reuse': raise ValueError('Discovery must be full or reuse; quickcheck is a separate profile.')
        manifest=json.loads((root/'stage1/run_manifest.json').read_text(encoding='utf-8'))
        if manifest.get('status')!='complete': raise ValueError('Discovery is incomplete')
        if manifest.get('input_sha256')!=sha(cfg.input_csv):raise ValueError('Discovery belongs to a different input corpus.')
        discovery_fields = ('embedding_model','embedding_revision','search_iterations','topic_min','topic_max','random_seed','seed_umap','refit_per_solution','umap_space','hdbscan_space')
        for field in discovery_fields:
            if manifest.get('config', {}).get(field) != getattr(cfg, field):
                raise ValueError(f'Discovery settings changed ({field}); use a new output directory.')
        if manifest.get('fitted_model_sha256')!=sha(root/'stage1/best_model/fitted_model.pkl'):raise ValueError('Saved discovery model checksum changed.')
        state['stages']['discovery']='passed';save()
        if __package__:
            from .stage2_democratic_naming import run_stage2
        else:
            from stage2_democratic_naming import run_stage2
        if __package__:
            from .stage3_synthesis_worksheet import run_stage3
        else:
            from stage3_synthesis_worksheet import run_stage3
        if __package__:
            from .stage4_classification import run_stage4
        else:
            from stage4_classification import run_stage4
        if __package__:
            from .stage5_inference import run_stage5
        else:
            from stage5_inference import run_stage5
        run_stage2(cfg);state['stages']['naming']='passed';save()
        run_stage3(cfg);synthetic_review(cfg);state['stages']['synthesis']='synthetic-oracle';save()
        run_stage4(cfg);state['stages']['classification']='passed';save()
        run_stage5(cfg);state['stages']['inference']='passed';save()
        report=validate_outputs(cfg)
        state['status']='passed'
        state['verification']=report
    except Exception as error:
        state['status']='failed';state['error_type']=type(error).__name__;state['error']=str(error);raise
    finally:
        if (root/'api_ledger.sqlite').exists():
            if __package__:
                from .api_budget import ApiBudget
            else:
                from api_budget import ApiBudget
            state['api_usage']=ApiBudget(cfg).export()
        state['finished_at']=datetime.now(timezone.utc).isoformat();save()
    print('Synthetic workflow passed. Human validation and historical recomputation are not claimed.')
    return state
