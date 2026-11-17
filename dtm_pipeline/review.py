"""Bind synthesis decisions to their evidence; never invent human review."""
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
if __package__:
    from .config import PipelineConfig
else:
    from config import PipelineConfig
if __package__:
    from .provenance import input_kind
else:
    from provenance import input_kind


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def review_inputs(cfg):
    root=Path(cfg.output_dir)
    return {'corpus_sha256':sha(cfg.input_csv),
            'discovery_corpus_sha256':sha(cfg.discovery_input_csv or cfg.input_csv),
            'topic_words_sha256':sha(root/'stage1/best_model/topic_words.csv'),
            'assignments_sha256':sha(root/'stage1/best_model/classified_tweets.csv'),
            'naming_sha256':sha(root/'stage2/topic_names.csv'),
            'theme_map_sha256':sha(root/'stage3/theme_map.csv'),
            'themes':list(cfg.themes)}


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


def require_review(cfg):
    record_path=Path(cfg.output_dir)/'stage3/review_record.json'
    if not record_path.exists(): raise ValueError('A current stage3/review_record.json is required before classification. Complete actual researcher review.')
    record=json.loads(record_path.read_text(encoding='utf-8'))
    if any(record.get(k)!=v for k,v in review_inputs(cfg).items()):
        raise ValueError('Synthesis review is stale: evidence, taxonomy or mapping changed.')
    if not (record.get('review_mode')=='human' and record.get('human_review_performed') is True and record.get('decision')=='approved' and valid_reviewers(record.get('reviewers'))):
        raise ValueError('Actual two-researcher approval must be recorded before classification.')
    return record
