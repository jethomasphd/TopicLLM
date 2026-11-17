"""Verify the released original Study 1 data without ML or paid API calls."""
import csv, hashlib, json
from pathlib import Path
from collections import Counter
if __package__:
    from .config import DEMO_DIR
else:
    from config import DEMO_DIR

def verify_study1(data_dir=None):
    root=Path(data_dir or Path(DEMO_DIR)/'study1')
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    for name,item in manifest['files'].items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError(f'Study 1 checksum mismatch: {name}')
    def read(name):
        with (root/name).open(encoding='utf-8',newline='') as stream:return list(csv.DictReader(stream))
    raw,full,analysis,discovery=[read(n+'.csv') for n in ['collection','full','analysis','discovery']]
    seen=set();retained=[]
    for row in raw:
        if row['tweet'] in seen:continue
        seen.add(row['tweet'])
        if row['brand']=='Topo Chico Hard' or row['date'].startswith('2021-08'):continue
        retained.append(row)
    by_id={r['post_id']:r for r in retained}
    order=json.loads((root/'retained-order.json').read_text())
    if len(order)!=len(set(order)) or set(order)!=set(by_id) or [by_id[i] for i in order]!=full:
        raise ValueError('The released full cohort does not reconstruct from the collection records.')
    if [r for r in full if r['tweet'].strip()]!=analysis:raise ValueError('Nonempty analysis cohort differs.')
    if len(discovery)!=704 or any(not r['tweet'].strip() for r in discovery):raise ValueError('Invalid discovery cohort.')
    brands=dict(Counter(r['brand'] for r in full))
    counts={'collected':len(raw),'full':len(full),'brands':len(brands),'blank_text':len(full)-len(analysis),'analysis_nonempty':len(analysis),'discovery':len(discovery)}
    if counts!=manifest['counts'] or brands!=manifest['brand_counts']:raise ValueError('Study 1 count mismatch.')
    return {'mode':'original-study1-integrity-check','counts':counts,'files_verified':len(manifest['files']),
            'cohort_reconstructed':True,'api_calls':0,'historical_output_replication_claimed':False}

def quickcheck(cfg):
    report=verify_study1();out=Path(cfg.output_dir);out.mkdir(parents=True,exist_ok=True)
    (out/'study1-integrity.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report
