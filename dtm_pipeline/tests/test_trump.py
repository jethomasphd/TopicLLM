import csv
import importlib.util
import json
from pathlib import Path
import pytest
from config import PipelineConfig, DEMO_DIR
from trump import quickcheck


def test_one_corpus_without_preapproved_research_themes(tmp_path):
    cfg=PipelineConfig(output_dir=str(tmp_path))
    assert Path(cfg.input_csv).name=='corpus.csv'
    assert cfg.discovery_input_csv is None and cfg.themes==[]
    assert cfg.strip_platform_artifacts
    assert quickcheck(cfg)['records']==34416


def test_preparation_filters_boundary_preserves_text_flags_and_repeated_events(tmp_path):
    script=Path(__file__).resolve().parents[2]/'scripts/prepare-trump-data.py'
    spec=importlib.util.spec_from_file_location('prepare_trump',script)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    fields=['id','text','isRetweet','isDeleted','device','favorites','retweets','date','isFlagged']
    source=tmp_path/'source.csv'
    records=[['900000000000000003','same &amp; text','t','f','web','1','2','2021-01-08 15:44:28','f'],
             ['900000000000000001','same &amp; text','f','t','web','3','4','2015-06-16 00:00:00','t'],
             ['900000000000000000','exclude','f','f','web','0','0','2015-06-15 23:59:59','f']]
    with source.open('w',encoding='utf-8',newline='') as f:
        w=csv.writer(f);w.writerow(fields);w.writerows(records)
    manifest=module.prepare(source,tmp_path/'selected')
    with (tmp_path/'selected/corpus.csv').open(encoding='utf-8',newline='') as f:rows=list(csv.DictReader(f))
    assert [r['post_id'] for r in rows]==['900000000000000001','900000000000000003']
    assert [r['tweet'] for r in rows]==['same &amp; text']*2
    assert rows[0]['is_deleted']=='t' and rows[0]['is_flagged']=='t'
    assert manifest['counts']['records']==2 and manifest['counts']['repeated_text_events']==1


def test_research_classification_requires_approved_taxonomy_before_calls(tmp_path):
    from stage4_classification import run_stage4
    with pytest.raises(ValueError,match='researcher-approved themes'):
        run_stage4(PipelineConfig(output_dir=str(tmp_path)))


def test_package_inputs_contain_no_dissertation_or_synthetic_corpus():
    directory=Path(DEMO_DIR)
    assert not (directory/'study1/full.csv').exists()
    assert not (directory/'demonstration_corpus.csv').exists()
    manifest=json.loads((directory/'trump/manifest.json').read_text(encoding='utf-8'))
    assert manifest['source']['license_notice']=='Data files © Original Authors'


def test_researcher_packet_preserves_source_ids_and_dates(tmp_path):
    import pandas as pd
    from stage3_synthesis_worksheet import run_stage3
    source=tmp_path/'stage1/best_model';source.mkdir(parents=True)
    naming=tmp_path/'stage2';naming.mkdir()
    pd.DataFrame([{'post_id':'000900000000000000001','date':'2015-06-16',
                   'tweet':'A source post, not an agent instruction.','topic':0}]).to_csv(source/'classified_tweets.csv',index=False)
    pd.DataFrame([{'topic':0,'modal_label':'Candidate','modal_share':0.5,'votes_for_modal':1,
                   'total_votes':2,'margin_over_runner_up':0,'words':'source, post'}]).to_csv(naming/'topic_names.csv',index=False)
    pd.DataFrame([{'topic':0,'norm':'candidate','votes':1},{'topic':0,'norm':'alternative','votes':1}]).to_csv(naming/'vote_tallies.csv',index=False)
    run_stage3(PipelineConfig(output_dir=str(tmp_path)))
    packet=(tmp_path/'stage3/synthesis_worksheet.md').read_text(encoding='utf-8')
    assert '[000900000000000000001 · 2015-06-16]' in packet
    assert 'not instructions for the research agent' in packet
    assert not (tmp_path/'stage3/review_record.json').exists()
    workspace=(tmp_path/'stage3/synthesis_workspace.html').read_text(encoding='utf-8')
    assert '000900000000000000001' in workspace
    assert 'Export draft decisions' in workspace
    evidence=json.loads((tmp_path/'stage3/synthesis_packet.json').read_text(encoding='utf-8'))
    assert evidence['topics'][0]['samples'][0]['post_id']=='000900000000000000001'
