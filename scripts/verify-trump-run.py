"""Verify a completed tutorial discovery run, including reloading your trusted model.

Run in the same ML environment that created the local fitted_model.pkl.
Usage: python scripts/verify-trump-run.py --run runs/trump
Never point this command at a pickle from an untrusted source.
"""
import argparse
import csv
import hashlib
import json
import sys
from dataclasses import fields
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def verify(run):
    from bertopic import BERTopic
    run = Path(run)
    stage = run / 'stage1'
    read = lambda p: json.loads(p.read_text(encoding='utf-8'))
    rows = lambda p: list(csv.DictReader(p.open(encoding='utf-8', newline='')))
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    corpus = ROOT / 'docs/data/trump/corpus.csv'
    record = read(stage / 'run_manifest.json')
    if record['status'] != 'complete' or record['input_sha256'] != sha(corpus):
        raise ValueError('A completed run on the canonical tutorial corpus is required.')
    assignments = rows(stage / 'best_model/classified_tweets.csv')
    exclusions = rows(stage / 'excluded_empty.csv')
    from dtm_pipeline.config import PipelineConfig
    from dtm_pipeline.sampling import read_selected
    cfg=PipelineConfig(**{key:value for key,value in record['config'].items() if key in {f.name for f in fields(PipelineConfig)}})
    cfg.input_csv=str(corpus)
    selected,selection=read_selected(cfg,'discovery')
    source_ids = {r['post_id'] for r in selected}
    observed_ids = [r['post_id'] for r in assignments + exclusions]
    if len(observed_ids) != len(source_ids) or set(observed_ids) != source_ids:
        raise ValueError('Modeled and excluded records must partition the source IDs exactly.')
    candidates = read(stage / 'all_iteration_results.json')
    draws = record['config']['search_iterations']
    ceilings = record['config']['topic_max'] - record['config']['topic_min'] + 1
    if len(candidates['iterations']) != draws or sum(len(i['details']) for i in candidates['iterations']) != draws * ceilings:
        raise ValueError('The declared candidate search is incomplete.')
    model_path = stage / 'best_model/fitted_model.pkl'
    if sha(model_path) != record['fitted_model_sha256']:
        raise ValueError('Fitted model hash differs from its recorded hash.')
    model = BERTopic.load(str(model_path))
    if list(model.topics_) != [int(r['topic']) for r in assignments]:
        raise ValueError('Reloaded model assignments differ from the published assignment file.')
    result = {
        'status': 'complete', 'scope': 'campaign-only discovery' if cfg.discovery_window else 'prior whole-archive diagnostic',
        'historical_replication': False, 'api_calls': 0,
        'selected_model_reload_verified': True,
        'input_records': len(source_ids), 'discovery_records': len(assignments),
        'source_records':selection['source_records'],'selection':selection,
        'excluded_empty': len(exclusions), 'search_draws': draws,
        'candidate_ceilings': draws * ceilings,
        'input_sha256': sha(corpus), 'fitted_model_sha256': sha(model_path),
        'verified_at': datetime.now(timezone.utc).isoformat(),
        'human_review_performed': False, 'classifier_validated': False,
    }
    existing = run / 'verification.json'
    existing.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    print(json.dumps(verify(parser.parse_args().run), indent=2))
