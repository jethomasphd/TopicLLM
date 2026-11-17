"""Build the author-authorized Study 1 release from a local recovered archive.

Only brand, date, verbatim tweet text and stable record IDs are released.
Study 2 and collection personnel/administrative fields are never read here.
Usage: python scripts/build-study1-release.py --archive-folder PATH --run-folder PATH --stopwords PATH
"""
from pathlib import Path
import argparse, csv, hashlib, json, re, shutil
from collections import defaultdict, Counter
import pandas as pd

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--archive-folder',type=Path,required=True)
parser.add_argument('--run-folder',type=Path,required=True)
parser.add_argument('--stopwords',type=Path,required=True)
args=parser.parse_args()
root=Path(__file__).resolve().parents[1];out=root/'docs/data/study1';out.mkdir(parents=True,exist_ok=True)
TEXT='Verbatim text in tweet (exclude emoji and space out hashtags)'
BRAND='Name of Company';DATE='Date of Tweet'
read=lambda name:pd.read_csv(args.archive_folder/name,dtype=str,keep_default_na=False)
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
raw=read('deduplicated_alcohol_data.csv');full=read('deduplicated_full_dataset.csv')
lock=read('deduplicated_lockdown_dataset.csv');discovery=read('tweet_data.csv')
lookup=defaultdict(list)
for i,row in raw.iterrows():lookup[tuple(row)].append(i+1)
def minimize(frame):
    rows=[]
    for _,r in frame.iterrows():
        number=lookup[tuple(r)][0]
        rows.append({'post_id':f's1-{number:06d}','brand':r[BRAND],'date':pd.to_datetime(r[DATE],format='mixed').date().isoformat(),'tweet':r[TEXT]})
    return pd.DataFrame(rows)
collected=minimize(raw)
# Give identical collection rows distinct source-row IDs; retained rows use first occurrence.
collected['post_id']=[f's1-{i:06d}' for i in range(1,len(raw)+1)]
released=minimize(full)
assert len(released)==5872 and released.brand.nunique()==11 and released.post_id.is_unique
nonempty=released.loc[released.tweet.str.strip().ne('')].copy()
lock_nonempty=lock.loc[lock[TEXT].ne('')].reset_index(drop=True)
assert len(lock_nonempty)==len(discovery)==704
discovered=minimize(lock_nonempty)
def repair_run(m):
    text=m.group()
    for _ in range(3):
        try:fixed=b''.join(bytes([ord(c)]) if 0x80<=ord(c)<=0x9f else c.encode('cp1252') for c in text).decode('utf-8')
        except (UnicodeError,ValueError):break
        if fixed==text:break
        text=fixed
    return text
repair=lambda value:re.sub(r'[^\x00-\x7f]+',repair_run,value)
assert discovered.tweet.map(repair).tolist()==discovery[TEXT].map(repair).tolist()
# Preserve the actual archived discovery input, including its encoding artifacts.
# A separate display field retains the readable collection transcription.
discovered['display_text']=discovered.tweet
discovered['tweet']=discovery[TEXT].tolist()
for name,frame in [('collection.csv',collected),('full.csv',released),('analysis.csv',nonempty),('discovery.csv',discovered)]:
    frame.to_csv(out/name,index=False,lineterminator='\n')
shutil.copyfile(args.stopwords,out/'stopwords.txt')
(out/'retained-order.json').write_text(json.dumps(released.post_id.tolist(),separators=(',',':'))+'\n')
stage=args.run_folder/'full-search/stage1'
parameters=json.loads((stage/'best_model/parameters.json').read_text())
run=json.loads((args.run_folder/'verification.json').read_text())
assign=pd.read_csv(stage/'best_model/classified_tweets.csv')
assert assign.archive_record.tolist()==list(range(1,705)) and assign.tweet.tolist()==discovered.tweet.tolist()
assignment_rows=[{'post_id':discovered.iloc[i].post_id,'topic':int(topic)} for i,topic in enumerate(assign.topic)]
pd.DataFrame(assignment_rows).to_csv(out/'discovery-assignments.csv',index=False,lineterminator='\n')
import ast
words=pd.read_csv(stage/'best_model/topic_words.csv')
topics=[]
for row in words.to_dict('records'):
    if row['Topic']==-1:continue
    ids=[a['post_id'] for a in assignment_rows if a['topic']==row['Topic']]
    topics.append({'id':str(row['Topic']),'count':int(row['Count']),'words':ast.literal_eval(row['Representation']), 'example_ids':ids[:4]})
source_record_by_id={r['post_id']:r for r in collected.to_dict('records')}
examples=[{'id':str(i),'post_id':r['post_id'],'brand':r['brand'],'date':r['date'],'text':r['tweet']} for i,r in enumerate(nonempty.to_dict('records'))]
lookup_examples={e['post_id']:e['id'] for e in examples}
for t in topics:t['example_ids']=[lookup_examples[p] for p in t['example_ids'] if p in lookup_examples]
reported=json.loads((root/'docs/data/study.json').read_text())
live={'mode':'original-study1-illustration','domain':'public alcohol-brand tweets during the COVID-19 pandemic',
      'themes':[p['theme'] for p in reported['prevalence']], 'topics':[{**t,'words':', '.join(t['words'])} for t in topics], 'examples':examples}
(root/'docs/data/live-examples.json').write_text(json.dumps(live,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
periods={'pre':1707,'peri':806,'post':3106,'outside':253}
assert len(nonempty)==5871
manifest={'version':'study1-v1','mode':'original-study1-illustration','release_authorization':'Author authorized public release of Study 1 brand data on 2026-11-16; Study 2 user data excluded.',
 'scope':'Original Study 1 data and an illustrative modern rerun; exact historical output replication is not the objective.',
 'variability':'Topic models and LLMs include probabilistic steps. A fresh run can group or label some posts differently, especially when the random seed, model, or software version changes.',
 'counts':{'collected':6174,'full':5872,'brands':11,'blank_text':1,'analysis_nonempty':5871,'discovery':704},
 'cleaning':{'exact_text_duplicates':267,'topo_chico_removed':20,'august_2021_removed':15,'order':'Exact-text deduplication keeping first; exclude Topo Chico and August 2021; retain archived row order.'},
 'period_counts':periods,'brand_counts':released.brand.value_counts().to_dict(),
 'discovery_window':{'start':'2020-03-25','end':'2020-05-31','before_dedup':742,'after_dedup':705,'nonempty':704},
 'encoding':'discovery.csv tweet preserves archived model-input values; display_text is the collection transcription for reading. Full and analysis files preserve collection text. No silent normalization is applied to model inputs.',
 'source_hashes':{name:sha(args.archive_folder/name) for name in ['deduplicated_alcohol_data.csv','deduplicated_full_dataset.csv','deduplicated_lockdown_dataset.csv','tweet_data.csv','Summary Table.xlsx']},
 'files':{p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(out.iterdir()) if p.suffix in ('.csv','.txt')},
 'data_fields':['post_id','brand','date','tweet'],'excluded_fields':'Collector identities, emails, collection timestamps, screenshot links, annotation fields and all Study 2 records.',
 'reference_run':{'parameters':parameters,'topics':topics,'outliers':int((assign.topic==-1).sum()),'documents':704,'api_calls':0,'human_review_performed':False,
                  'environment':json.loads((stage/'run_manifest.json').read_text())['environment'],'seed_checks':[{k:v for k,v in r.items() if k!='topics'} for r in run['results']]},
 'historical_comparison':'Seven topics and five researcher-defined themes are reported dissertation results. The recorded modern run selected five statistical topics; these are not asserted to be the same five themes.',
 'benchmark':'No final human-validation benchmark is asserted or bundled for research. Researchers supply an independently annotated benchmark for research classification.',
 'table_note':'The recovered data and summary workbook agree on brand counts. Five name/count pairings in printed Table 1 differ; the dissertation is preserved unchanged. Dataset counts are reported directly.'}
(out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for filename in ['all_iteration_results.json','run_manifest.json']:
    data=json.loads((stage/filename).read_text())
    if filename=='run_manifest.json':
        data['config']['input_csv']='study1/discovery.csv';data['config']['output_dir']='runs/study1-discovery';data['config']['stopwords_file']='study1/stopwords.txt'
        data['config']['benchmark_csv']='<unused legacy fixture; discovery-only run>'
        data['public_export']={'note':'Machine-local paths replaced by public equivalents. input_sha256 identifies the archived input file, not the minimized release CSV. Its ordered tweet values are preserved in the release. No benchmark or API stages ran.', 'released_discovery_sha256':sha(out/'discovery.csv')}
    (out/filename).write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'released':manifest['counts'],'live_examples':len(examples),'topics':len(topics)}))
