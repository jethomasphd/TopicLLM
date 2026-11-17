"""Prepare the one public tutorial corpus from Kaggle version 1, without relabeling text.

Usage: python scripts/prepare-trump-data.py --source /path/to/tweets.csv
The full upstream archive is not bundled: only records on/after 2015-06-16.
"""
import argparse,csv,hashlib,io,json
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
START='2015-06-16'
SOURCE_URL='https://www.kaggle.com/datasets/codebreaker619/donald-trump-tweets-dataset'

def prepare(source, destination):
    raw=Path(source).read_bytes()
    rows=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
    required={'id','text','date','isRetweet','isDeleted','device','favorites','retweets','isFlagged'}
    if not rows or not required.issubset(rows[0]): raise ValueError('Expected Kaggle tweets.csv schema.')
    for row in rows: datetime.strptime(row['date'],'%Y-%m-%d %H:%M:%S')
    selected=sorted((r for r in rows if r['date'][:10]>=START),key=lambda r:(r['date'],int(r['id'])))
    if len({r['id'] for r in selected})!=len(selected):raise ValueError('Duplicate source IDs require review.')
    if any(not r['text'].strip() for r in selected):raise ValueError('Blank source text requires review.')
    fields=['post_id','tweet','date','timestamp','is_retweet','is_deleted','device','favorites','retweets','is_flagged']
    records=[dict(zip(fields,[r['id'],r['text'],r['date'][:10],r['date'],r['isRetweet'],r['isDeleted'],r['device'],r['favorites'],r['retweets'],r['isFlagged']])) for r in selected]
    dest=Path(destination);dest.mkdir(parents=True,exist_ok=True)
    with (dest/'corpus.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(records)
    stopwords='rt, https, http, co, amp, realdonaldtrump\n'
    (dest/'stopwords.txt').write_text(stopwords,encoding='utf-8',newline='\n')
    periods={'campaign':['2015-06-16','2016-11-08'],'transition':['2016-11-09','2017-01-19'],'presidency':['2017-01-20',selected[-1]['date'][:10]]}
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    manifest={
        'schema_version':1,'dataset':'trump-tweets-2015-2021','mode':'public-archive-tutorial',
        'source':{'title':'Donald Trump Tweets Dataset','publisher':'CodeBreaker619','url':SOURCE_URL,'version':1,'updated':'2021-01-10','download_url':'https://www.kaggle.com/api/v1/datasets/download/codebreaker619/donald-trump-tweets-dataset','source_csv_sha256':hashlib.sha256(raw).hexdigest(),'license_notice':'Data files © Original Authors'},
        'selection':{'start_inclusive':START,'end_inclusive':selected[-1]['date'][:10],'timestamp_basis':'Source timestamps without timezone offsets; no timezone conversion applied. Selection uses the source calendar date.','rule':'Keep every source record with date >= 2015-06-16, sort by timestamp then integer ID. Preserve tweet text and all source flags. Retweets and repeated text remain distinct posting events.'},
        'counts':{'source_records':len(rows),'records':len(records),'excluded_before_start':len(rows)-len(records),'unique_ids':len(records),'retweets':sum(r['isRetweet']=='t' for r in selected),'flagged_deleted':sum(r['isDeleted']=='t' for r in selected),'repeated_text_events':len(selected)-len({r['text'] for r in selected}),'blank_text':0},
        'first_timestamp':selected[0]['date'],'last_timestamp':selected[-1]['date'],
        'year_counts':dict(sorted(Counter(r['date'][:4] for r in selected).items())),
        'periods':periods,'period_counts':{p:sum(a<=r['date'][:10]<=b for r in selected) for p,(a,b) in periods.items()},
        'files':{n:{'sha256':sha(dest/n),'bytes':(dest/n).stat().st_size} for n in ['corpus.csv','stopwords.txt']},
        'scope':'Posts captured by the selected archive, including retweets. Account activity is not equivalent to personally authored statements. Ends 2021-01-08, before the first term ended. No archive completeness guarantee or fact verification of tweet claims is made.'
    }
    (dest/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    return manifest

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source',required=True);parser.add_argument('--output',default=str(ROOT/'docs/data/trump'))
    args=parser.parse_args();m=prepare(args.source,args.output);print(json.dumps({'counts':m['counts'],'first':m['first_timestamp'],'last':m['last_timestamp']},indent=2))
