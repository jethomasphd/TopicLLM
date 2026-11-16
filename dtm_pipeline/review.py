"""Bind synthesis decisions to their evidence; never invent human review."""
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
if __package__:
    from .config import DEMO_DIR, PipelineConfig
else:
    from config import DEMO_DIR, PipelineConfig
if __package__:
    from .provenance import input_kind
else:
    from provenance import input_kind


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def review_inputs(cfg):
    root=Path(cfg.output_dir)
    return {'corpus_sha256':sha(cfg.input_csv),
            'topic_words_sha256':sha(root/'stage1/best_model/topic_words.csv'),
            'assignments_sha256':sha(root/'stage1/best_model/classified_tweets.csv'),
            'naming_sha256':sha(root/'stage2/topic_names.csv'),
            'theme_map_sha256':sha(root/'stage3/theme_map.csv'),
            'themes':list(cfg.themes)}


def exact_synthetic_inputs(cfg):
    for path,name in [(cfg.input_csv,'demonstration_corpus.csv'),(cfg.benchmark_csv,'demonstration_benchmark.csv'),(cfg.stopwords_file,'demonstration_stopwords.txt')]:
        if input_kind(path,name)!='bundled-synthetic':
            raise ValueError('Synthetic automation requires the exact bundled corpus, benchmark and stopwords.')
    for name in ('demonstration_ground_truth.csv','study.json'):
        if input_kind(Path(DEMO_DIR)/name,name)!='bundled-synthetic':
            raise ValueError('Bundled synthetic truth or study targets changed; restore the declared fixture.')
    reference = PipelineConfig()
    for field in ('themes', 'none_label', 'periods', 'alpha'):
        if json.dumps(getattr(cfg, field), sort_keys=True) != json.dumps(getattr(reference, field), sort_keys=True):
            raise ValueError('Synthetic automation requires the bundled taxonomy and inference settings.')


def valid_reviewers(reviewers):
    if not isinstance(reviewers, list) or not all(isinstance(name, str) for name in reviewers):
        return False
    names = [name.strip().casefold() for name in reviewers]
    return len(set(names)) >= 2 and all(names) and not any(name in ('test','agent','ai','todo','reviewer','unknown') for name in names)


def record_human_review(cfg, reviewers):
    reviewers=[name.strip() for name in reviewers if name.strip()]
    if not valid_reviewers(reviewers):
        raise ValueError('Record at least two distinct actual researcher names after their review.')
    record={**review_inputs(cfg),'review_mode':'human','human_review_performed':True,
            'decision':'approved','reviewers':reviewers,'recorded_at':datetime.now(timezone.utc).isoformat()}
    Path(cfg.output_dir,'stage3','review_record.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    return record


def synthetic_review(cfg):
    exact_synthetic_inputs(cfg)
    if cfg.run_mode!='synthetic-e2e': raise ValueError('Synthetic oracle review requires the explicit synthetic-e2e profile.')
    root=Path(cfg.output_dir)
    assignment=pd.read_csv(root/'stage1/best_model/classified_tweets.csv')
    truth=pd.read_csv(Path(DEMO_DIR)/'demonstration_ground_truth.csv')[['post_id','theme']]
    if assignment.post_id.duplicated().any(): raise ValueError('Duplicate assignment IDs')
    joined=assignment.drop(columns=['theme'],errors='ignore').merge(truth,on='post_id',validate='one_to_one')
    if len(joined)!=len(pd.read_csv(cfg.input_csv)): raise ValueError('Assignments do not cover the synthetic corpus.')
    names=pd.read_csv(root/'stage2/topic_names.csv')
    rows=[]
    for item in names.to_dict('records'):
        group=joined[joined.topic==item['topic']]
        counts=group.theme.value_counts()
        if counts.empty: raise ValueError('Topic has no source documents')
        winner=str(counts.index[0])
        rows.append({'topic':item['topic'],'modal_label':item['modal_label'],
                     'theme':winner if winner in cfg.themes else '',
                     'synthetic_majority_label':winner,'synthetic_purity':int(counts.iloc[0])/len(group),'documents':len(group)})
    pd.DataFrame(rows).to_csv(root/'stage3/theme_map.csv',index=False,lineterminator='\n')
    record={**review_inputs(cfg),'review_mode':'synthetic-oracle','human_review_performed':False,'decision':'synthetic-test-only',
            'reviewers':[],'rule':'Majority generator-truth theme per discovered topic; residual-majority topics stay unmapped.',
            'truth_sha256':sha(Path(DEMO_DIR)/'demonstration_ground_truth.csv'),'recorded_at':datetime.now(timezone.utc).isoformat()}
    (root/'stage3/review_record.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    return record


def require_review(cfg):
    record_path=Path(cfg.output_dir)/'stage3/review_record.json'
    if not record_path.exists(): raise ValueError('A current stage3/review_record.json is required before classification. Complete researcher review or use the explicit synthetic-e2e profile.')
    record=json.loads(record_path.read_text(encoding='utf-8'))
    if any(record.get(k)!=v for k,v in review_inputs(cfg).items()):
        raise ValueError('Synthesis review is stale: evidence, taxonomy or mapping changed.')
    if record.get('review_mode')=='synthetic-oracle':
        exact_synthetic_inputs(cfg)
        if cfg.run_mode!='synthetic-e2e' or record.get('human_review_performed') is not False:
            raise ValueError('Synthetic oracle decisions cannot authorize a research run.')
    elif not (record.get('review_mode')=='human' and record.get('human_review_performed') is True and record.get('decision')=='approved' and valid_reviewers(record.get('reviewers'))):
        raise ValueError('Actual two-researcher approval must be recorded before classification.')
    if input_kind(cfg.input_csv,'demonstration_corpus.csv')!='bundled-synthetic' and input_kind(cfg.benchmark_csv,'demonstration_benchmark.csv')=='bundled-synthetic':
        raise ValueError('A research corpus cannot use the bundled synthetic benchmark. Supply a separately annotated research benchmark.')
    return record
