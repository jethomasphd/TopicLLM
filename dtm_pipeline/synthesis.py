"""Create a local human synthesis workspace from measured topic evidence."""
import hashlib
import json
from pathlib import Path
import pandas as pd


def render_synthesis_workspace(cfg, output=None):
    root=Path(cfg.output_dir)
    source=root/'stage1/best_model/classified_tweets.csv'
    names_path=root/'stage2/topic_names.csv'
    frame=pd.read_csv(source,dtype={'post_id':str},keep_default_na=False)
    names=pd.read_csv(names_path,keep_default_na=False)
    tallies=pd.read_csv(root/'stage2/vote_tallies.csv',keep_default_na=False)
    topics=[]
    for row in names.sort_values('topic').to_dict('records'):
        records=frame.loc[frame.topic==row['topic']]
        sample=records.sample(min(15,len(records)),random_state=cfg.random_seed)
        topics.append({**row,'count':len(records),
                       'samples':sample[['post_id','date','tweet']].to_dict('records') if 'date' in sample else sample[['post_id','tweet']].to_dict('records'),
                       'top_names':tallies.loc[tallies.topic==row['topic']].head(5).to_dict('records')})
    outliers=frame.loc[frame.topic==-1]
    sample=outliers.sample(min(30,len(outliers)),random_state=cfg.random_seed)
    hashes={str(p.relative_to(root)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,names_path,root/'stage2/vote_tallies.csv']}
    packet={'schema_version':1,'topics':topics,'modeled_records':len(frame),'outlier_count':len(outliers),
            'outlier_samples':sample[[c for c in ['post_id','date','tweet'] if c in sample]].to_dict('records'),
            'discovery_window':cfg.discovery_window,'target_window':cfg.target_window,'source_hashes':hashes,
            'none_label':cfg.none_label,'sample_seed':cfg.random_seed,
            'corpus_sha256':hashlib.sha256(Path(cfg.input_csv).read_bytes()).hexdigest(),
            'discovery_input_sha256':hashlib.sha256(Path(cfg.discovery_input_csv or cfg.input_csv).read_bytes()).hexdigest()}
    packet['packet_sha256']=hashlib.sha256(json.dumps(packet,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    payload=json.dumps(packet,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    template=Path(__file__).with_name('synthesis_ui.html').read_text(encoding='utf-8')
    path=Path(output) if output else root/'stage3/synthesis_workspace.html'
    path.parent.mkdir(parents=True,exist_ok=True)
    logic=Path(__file__).with_name('synthesis_logic.js').read_text(encoding='utf-8')
    path.write_text(template.replace('__PACKET_JSON__',payload).replace('__GROUPING_LOGIC__',logic),encoding='utf-8',newline='\n')
    (root/'stage3/synthesis_packet.json').write_text(json.dumps(packet,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')
    return path
