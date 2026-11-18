"""Artificial review fixtures verify imports; they are not research decisions."""
import json
from pathlib import Path
import pandas as pd
import pytest
from dtm_pipeline.config import PipelineConfig
from dtm_pipeline.synthesis import render_synthesis_workspace
from dtm_pipeline.synthesis_review import import_review
from dtm_pipeline.review import require_review


def fixture(root):
    source=root/'source.csv'
    pd.DataFrame([{'post_id':'0001','tweet':'Artificial fixture </script> & text','date':'2016-01-01'}]).to_csv(source,index=False)
    model=root/'stage1/best_model';model.mkdir(parents=True)
    pd.DataFrame([{'post_id':'0001','tweet':'Artificial fixture </script> & text','date':'2016-01-01','topic':0}]).to_csv(model/'classified_tweets.csv',index=False)
    (model/'topic_words.csv').write_text('topic,words\n0,fixture\n')
    stage=root/'stage2';stage.mkdir()
    pd.DataFrame([{'topic':0,'modal_label':'Artificial proposal','modal_share':1,'votes_for_modal':2,'total_votes':2,'words':'fixture'}]).to_csv(stage/'topic_names.csv',index=False)
    pd.DataFrame([{'topic':0,'norm':'artificial proposal','votes':2}]).to_csv(stage/'vote_tallies.csv',index=False)
    settings={'input_csv':str(source),'output_dir':str(root),'discovery_window':['2015-06-16','2016-11-08'],'target_window':['2017-01-20','2021-01-08']}
    config=root/'config.json';config.write_text(json.dumps(settings))
    render_synthesis_workspace(PipelineConfig(**settings))
    packet=json.loads((root/'stage3/synthesis_packet.json').read_text())
    submitted={'decision':'human-consensus-submitted','human_review_performed':True,'reviewers':['Fixture researcher A','Fixture researcher B'],
        'packet_sha256':packet['packet_sha256'],'source_hashes':packet['source_hashes'],
        'theme_map':[{'topic':0,'modal_label':'Artificial proposal','theme':'Fixture category','excluded':False,'rationale':'Artificial import test.'}],
        'codebook':{'themes':{'Fixture category':'Meaning, inclusion, exclusion and boundary examples in an artificial fixture.'},'decision_rule':'Artificial rule.'},
        'review_notes':{'first':'Fixture interpretation.','second':'Fixture critique.','consensus':'Fixture agreement.'}}
    review=root/'review.json';review.write_text(json.dumps(submitted))
    return config,review,submitted


def test_complete_fixture_import_binds_evidence_and_refuses_overwrite(tmp_path):
    config,review,_=fixture(tmp_path)
    result=import_review(config,review,tmp_path/'approved.json')
    assert result['themes']==1
    cfg=PipelineConfig(**json.loads((tmp_path/'approved.json').read_text()))
    assert require_review(cfg)['reviewers']==['Fixture researcher A','Fixture researcher B']
    with pytest.raises(ValueError,match='overwrite'):import_review(config,review,tmp_path/'approved.json')


@pytest.mark.parametrize('change',['draft','evidence','source'])
def test_draft_or_changed_evidence_never_creates_approval(tmp_path,change):
    config,review,submitted=fixture(tmp_path)
    if change=='draft':
        submitted['decision']='draft';submitted['human_review_performed']=False
        review.write_text(json.dumps(submitted))
    elif change=='evidence':(tmp_path/'stage2/topic_names.csv').write_text('changed')
    else:(tmp_path/'source.csv').write_text('changed')
    with pytest.raises(ValueError):import_review(config,review,tmp_path/'approved.json')
    assert not (tmp_path/'stage3/review_record.json').exists()
    assert not (tmp_path/'approved.json').exists()


def test_untrusted_post_text_cannot_close_packet_script(tmp_path):
    fixture(tmp_path)
    page=(tmp_path/'stage3/synthesis_workspace.html').read_text()
    assert 'Artificial fixture </script>' not in page
    assert '\\u003c/script\\u003e' in page


def test_multiple_topics_import_as_one_human_theme(tmp_path):
    config,review,submitted=fixture(tmp_path)
    for relative in ['stage1/best_model/classified_tweets.csv','stage1/best_model/topic_words.csv','stage2/topic_names.csv','stage2/vote_tallies.csv']:
        path=tmp_path/relative
        frame=pd.read_csv(path,dtype={'post_id':str},keep_default_na=False)
        extra=frame.iloc[[0]].copy();extra['topic']=1
        if 'post_id' in extra:extra['post_id']='0002'
        pd.concat([frame,extra],ignore_index=True).to_csv(path,index=False)
    render_synthesis_workspace(PipelineConfig(**json.loads(config.read_text())))
    packet=json.loads((tmp_path/'stage3/synthesis_packet.json').read_text())
    submitted.update(packet_sha256=packet['packet_sha256'],source_hashes=packet['source_hashes'])
    submitted['theme_map'].append({**submitted['theme_map'][0],'topic':1,'rationale':'Second topic shares the same meaning in this artificial fixture.'})
    review.write_text(json.dumps(submitted))
    result=import_review(config,review,tmp_path/'approved.json')
    assert result['themes']==1
    mapping=pd.read_csv(tmp_path/'stage3/theme_map.csv')
    assert set(mapping.topic)=={0,1}
    assert mapping.theme.nunique()==1
    cfg=PipelineConfig(**json.loads((tmp_path/'approved.json').read_text()))
    require_review(cfg)
