"""Offline integrity check for the single public tutorial corpus. No model calls."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
if __package__:
    from .config import DEMO_DIR
else:
    from config import DEMO_DIR


def quickcheck(cfg):
    base = Path(DEMO_DIR) / 'trump'
    manifest = json.loads((base / 'manifest.json').read_text(encoding='utf-8'))
    for name, expected in manifest['files'].items():
        if hashlib.sha256((base / name).read_bytes()).hexdigest() != expected['sha256']:
            raise ValueError(f'Tutorial integrity mismatch: {name}')
    if Path(cfg.input_csv).read_bytes() != (base / 'corpus.csv').read_bytes():
        raise ValueError('quickcheck verifies the bundled tutorial. Inspect researcher inputs separately.')
    with (base / 'corpus.csv').open(encoding='utf-8', newline='') as f:
        rows = list(csv.DictReader(f))
    ids = [r['post_id'] for r in rows]
    assert len(rows) == len(set(ids)) == manifest['counts']['records'] == 34416
    assert min(r['date'] for r in rows) == '2015-06-16'
    assert max(r['date'] for r in rows) == '2021-01-08'
    assert all(r['tweet'].strip() and r['date'] == r['timestamp'][:10] for r in rows)
    assert dict(sorted(Counter(r['date'][:4] for r in rows).items())) == manifest['year_counts']
    assert sum(r['is_retweet'] == 't' for r in rows) == 9852
    report = {'status': 'pass', 'dataset': manifest['dataset'], 'records': len(rows),
              'window': ['2015-06-16', '2021-01-08'], 'unique_ids': len(set(ids)),
              'files_verified': list(manifest['files']), 'api_calls': 0,
              'scope': 'Data integrity only; not model validation or human review.'}
    output = Path(cfg.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / 'quickcheck.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report
