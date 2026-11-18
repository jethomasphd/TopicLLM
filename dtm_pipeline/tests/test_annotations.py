import csv
from pathlib import Path
from dtm_pipeline.config import PipelineConfig
from dtm_pipeline.annotations import draw_packets, adjudication_packet
import pytest


def test_annotation_sets_preserve_random_holdout_and_exclude_duplicate_text(tmp_path):
    source=tmp_path/'source.csv'
    with source.open('w',encoding='utf-8',newline='') as f:
        writer=csv.writer(f);writer.writerow(['post_id','tweet'])
        writer.writerows((str(i),f'text {i//2}') for i in range(40))
    cfg=PipelineConfig(input_csv=str(source))
    first=draw_packets(cfg,tmp_path/'first',5,8,12)
    second=draw_packets(cfg,tmp_path/'second',5,8,12)
    assert first==second
    read=lambda p:list(csv.DictReader(p.open(encoding='utf-8',newline='')))
    dev=read(tmp_path/'first/development_blank.csv');test=read(tmp_path/'first/evaluation_blank.csv')
    assert not {r['tweet'] for r in dev}&{r['tweet'] for r in test}
    assert all(not r['human_label'] for r in dev+test)
    with pytest.raises(ValueError,match='already exist'):draw_packets(cfg,tmp_path/'first',5,8,12)


def test_disagreements_are_not_resolved_by_software(tmp_path):
    paths=[tmp_path/'one.csv',tmp_path/'two.csv']
    for path,reviewer,labels in zip(paths,['Fixture Human A','Fixture Human B'],[['A','B'],['A','A']]):
        with path.open('w',encoding='utf-8',newline='') as f:
            w=csv.DictWriter(f,fieldnames=['post_id','tweet','human_label','reviewer']);w.writeheader()
            w.writerows({'post_id':str(i),'tweet':f'text {i}','human_label':label,'reviewer':reviewer} for i,label in enumerate(labels))
    output=tmp_path/'adjudication.csv'
    assert adjudication_packet(*paths,output)['unresolved_disagreements']==1
    rows=list(csv.DictReader(output.open(encoding='utf-8',newline='')))
    assert rows[1]['human_label']==''
    assert rows[1]['reviewer_1_label']=='B' and rows[1]['reviewer_2_label']=='A'
