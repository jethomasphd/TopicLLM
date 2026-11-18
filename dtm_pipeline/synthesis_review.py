"""Import an actually completed human review; never generate its decisions."""
import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
from dtm_pipeline.config import PipelineConfig
from dtm_pipeline.review import valid_reviewers, record_human_review


def import_review(config_path, review_path, output_config):
    settings=json.loads(Path(config_path).read_text(encoding='utf-8'))
    cfg=PipelineConfig(**settings)
    root=Path(cfg.output_dir)
    packet=json.loads((root/'stage3/synthesis_packet.json').read_text(encoding='utf-8'))
    submitted=json.loads(Path(review_path).read_text(encoding='utf-8'))
    if submitted.get('decision')!='human-consensus-submitted' or submitted.get('human_review_performed') is not True or not valid_reviewers(submitted.get('reviewers')):
        raise ValueError('An actually completed two-researcher review is required; a draft cannot authorize classification.')
    if submitted.get('packet_sha256')!=packet['packet_sha256'] or submitted.get('source_hashes')!=packet['source_hashes']:
        raise ValueError('Review evidence does not match this research packet.')
    for name,expected in packet['source_hashes'].items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest()!=expected:
            raise ValueError('Research evidence changed after the review packet was created.')
    if packet['discovery_window']!=cfg.discovery_window or packet['target_window']!=cfg.target_window:
        raise ValueError('The reviewed temporal design differs from the run configuration.')
    for key,path in [('corpus_sha256',cfg.input_csv),('discovery_input_sha256',cfg.discovery_input_csv or cfg.input_csv)]:
        if packet.get(key)!=hashlib.sha256(Path(path).read_bytes()).hexdigest():
            raise ValueError('The source corpus changed after the review packet was created.')
    mapping=submitted.get('theme_map',[])
    expected_topics={t['topic'] for t in packet['topics']}
    if len(mapping)!=len(expected_topics) or {r['topic'] for r in mapping}!=expected_topics:
        raise ValueError('Record exactly one disposition for every reviewed topic.')
    for row in mapping:
        expected=next(t for t in packet['topics'] if t['topic']==row['topic'])
        if row.get('modal_label')!=expected['modal_label'] or not isinstance(row.get('excluded'),bool):
            raise ValueError('Preserve each topic name and an explicit inclusion/exclusion decision.')
        if not isinstance(row.get('rationale'),str) or not row['rationale'].strip():
            raise ValueError('Every topic needs an actual grouping or exclusion rationale.')
        if row.get('excluded') is True:
            if row.get('theme'):raise ValueError('Excluded topics must have a blank theme.')
        elif not isinstance(row.get('theme'),str) or not row['theme'].strip():
            raise ValueError('Every included topic needs a theme.')
    themes=list(dict.fromkeys(r['theme'] for r in mapping if r['theme']))
    book=submitted.get('codebook',{})
    if not themes or set(book.get('themes',{}))!=set(themes) or not isinstance(book.get('decision_rule'),str) or not book['decision_rule'].strip():
        raise ValueError('The codebook must define exactly the mapped themes and a primary-theme rule.')
    if any(not isinstance(v,str) or not v.strip() for v in book['themes'].values()):
        raise ValueError('Complete every theme definition.')
    if any(not str(submitted.get('review_notes',{}).get(k,'')).strip() for k in ['first','second','consensus']):
        raise ValueError('Retain both researchers’ actual notes and consensus reasoning.')
    codebook=root/'stage3/codebook.json'
    map_path=root/'stage3/theme_map.csv'
    target=Path(output_config)
    if any(p.exists() for p in [codebook,map_path,root/'stage3/review_record.json',target]):
        raise ValueError('Refusing to overwrite an existing research decision. Declare a revised analysis explicitly.')
    if not (root/'stage1/best_model/topic_words.csv').is_file() or not target.parent.is_dir():
        raise ValueError('The topic-word evidence and destination directory must exist before importing review.')
    codebook.write_text(json.dumps(book,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')
    with map_path.open('w',encoding='utf-8',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=['topic','modal_label','theme','excluded','rationale'])
        writer.writeheader();writer.writerows({k:r[k] for k in writer.fieldnames} for r in mapping)
    cfg.themes=themes;cfg.codebook_path=str(codebook)
    settings.update(themes=themes,codebook_path=str(codebook))
    target.write_text(json.dumps(settings,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')
    (root/'stage3/human_synthesis_submission.json').write_bytes(Path(review_path).read_bytes())
    record_human_review(cfg,submitted['reviewers'])
    return {'themes':len(themes),'reviewers':submitted['reviewers'],'configuration':str(target),'next':'Prepare independent annotation packets. No classification has run.'}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',required=True)
    parser.add_argument('--review',required=True)
    parser.add_argument('--output-config',required=True)
    args=parser.parse_args()
    print(json.dumps(import_review(args.config,args.review,args.output_config),indent=2))

if __name__=='__main__':main()
