"""Publish compact evidence from a completed real run; never synthesize model results."""
import argparse,csv,hashlib,json,random,shutil,zipfile
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PRACTICE_THEMES=['Campaign and elections','Government and policy','Media and public criticism','International affairs','Economy and business','Personal and ceremonial messages']

def publish(run):
    run=Path(run);out=ROOT/'docs/data/trump';stage=run/'stage1'
    read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    dump=lambda p,obj:p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')
    verify=read(run/'verification.json')
    if verify['status']!='complete' or not verify['selected_model_reload_verified']:raise ValueError('A completed, reloaded model is required.')
    manifest=read(out/'manifest.json');record=read(stage/'run_manifest.json')
    if record['input_sha256']!=manifest['files']['corpus.csv']['sha256']:raise ValueError('Run uses a different corpus.')
    rows=lambda p:list(csv.DictReader(p.open(encoding='utf-8',newline='')))
    corpus=rows(out/'corpus.csv');assignments=rows(stage/'best_model/classified_tweets.csv');excluded=rows(stage/'excluded_empty.csv')
    if set(r['post_id'] for r in assignments)&set(r['post_id'] for r in excluded):raise ValueError('Overlapping modeled/excluded IDs.')
    if {r['post_id'] for r in assignments+excluded}!={r['post_id'] for r in corpus}:raise ValueError('Incomplete assignment coverage.')
    periods=manifest['periods']
    counts=lambda records:{key:sum(a<=r['date']<=b for r in records) for key,(a,b) in periods.items()}
    topics=[];rng=random.Random(42)
    for item in rows(stage/'topics_for_naming.csv'):
        ident=int(item['topic']);group=[r for r in assignments if int(r['topic'])==ident]
        examples=[{k:r[k] for k in ['post_id','tweet','date','is_retweet']} for r in rng.sample(group,min(3,len(group)))]
        topics.append({'id':ident,'words':item['words'].split(', '),'count':len(group),'period_counts':counts(group),'examples':examples})
    noise=[r for r in assignments if int(r['topic'])==-1]
    parameters=read(stage/'best_model/parameters.json');candidates=read(stage/'all_iteration_results.json')
    if len(candidates['iterations'])!=record['config']['search_iterations']:raise ValueError('Incomplete search.')
    statuses=Counter(d['status'] for it in candidates['iterations'] for d in it['details'])
    summary={'dataset':manifest['dataset'],'mode':'measured-discovery-tutorial','input_sha256':record['input_sha256'],
        'source_records':len(corpus),'discovery_records':len(assignments),'excluded_empty':len(excluded),
        'outliers':len(noise),'outlier_period_counts':counts(noise),'excluded_period_counts':counts(excluded),
        'periods':periods,'period_counts':manifest['period_counts'],'topics':topics,'parameters':parameters,
        'candidate_status_counts':dict(statuses),'verification':verify,'human_review_performed':False,'classifier_validated':False,
        'scope':'Recorded discovery on a public archive. Topic-assignment shares are descriptive; no human-validated theme prevalence is asserted.'}
    dump(out/'reference-run.json',summary)
    evidence=out/'reference';evidence.mkdir(exist_ok=True)
    for source,target in [('all_iteration_results.json','all_iteration_results.json'),('best_model/parameters.json','parameters.json'),('topics_for_naming.csv','topics_for_naming.csv'),('coherence_curve.png','coherence_curve.png')]:shutil.copy2(stage/source,evidence/target)
    with (evidence/'assignments.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['post_id','date','topic'],lineterminator='\n');writer.writeheader();writer.writerows({k:r[k] for k in writer.fieldnames} for r in assignments)
    with (evidence/'excluded.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['post_id','date','reason'],lineterminator='\n');writer.writeheader();writer.writerows({'post_id':r['post_id'],'date':r['date'],'reason':'empty_after_preprocessing'} for r in excluded)
    record['config'].update(input_csv='docs/data/trump/corpus.csv',discovery_input_csv=None,stopwords_file='docs/data/trump/stopwords.txt',output_dir='runs/trump')
    record['publication_note']='Local absolute paths normalized for portability. Input/model hashes and measured settings unchanged.'
    dump(evidence/'run_manifest.json',record);dump(evidence/'verification.json',verify)
    # Systematic chronological coverage plus the displayed seeded topic samples.
    lookup={r['post_id']:r for r in corpus};selected={corpus[round(i*(len(corpus)-1)/1023)]['post_id'] for i in range(1024)}
    selected.update(r['post_id'] for t in topics for r in t['examples'])
    sample=sorted((lookup[id] for id in selected),key=lambda r:(r['timestamp'],int(r['post_id'])))
    examples={'dataset':manifest['dataset'],'mode':'public-trump-tutorial','domain':record['config']['domain_context'],
        'themes':PRACTICE_THEMES,'taxonomy_status':'Unvalidated practice categories; not a researcher-approved theme map.',
        'selection':'1,024 evenly spaced chronological source rows including endpoints, plus three seeded examples per recorded topic; duplicate IDs removed.',
        'corpus_sha256':record['input_sha256'],'topics':[{'id':str(t['id']),'words':', '.join(t['words']),'count':t['count']} for t in topics],
        'examples':[{'id':'trump-'+r['post_id'],'post_id':r['post_id'],'text':r['tweet'],'date':r['date'],'is_retweet':r['is_retweet']} for r in sample]}
    dump(out/'live-examples.json',examples)
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(evidence.iterdir()) if p.is_file() and p.name!='artifact-integrity.json'}
    dump(evidence/'artifact-integrity.json',{'files':hashes})
    with zipfile.ZipFile(out/'reference-evidence.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for path in sorted(evidence.iterdir()):z.write(path,path.name)
    print(json.dumps({'topics':len(topics),'modeled':len(assignments),'outliers':len(noise),'excluded':len(excluded),'candidates':dict(statuses),'live_examples':len(sample),'coherence':parameters['coherence']},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);args=p.parse_args();publish(args.run)
