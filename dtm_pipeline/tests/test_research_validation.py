"""Artificial fixtures check gates; they are not research annotations."""
import json
from pathlib import Path
import sys
import pandas as pd
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import PipelineConfig
from review import record_human_review
from research_validation import run_validated_stage4, record_annotation_review, record_validation_review


def fixture(tmp_path, monkeypatch):
    corpus = tmp_path / 'source.csv'
    rows = [{'post_id':str(i), 'tweet':f'fixture {i}', 'date':'2018-01-01'} for i in range(6)]
    pd.DataFrame(rows).to_csv(corpus, index=False)
    dev, test = tmp_path/'dev.csv', tmp_path/'heldout.csv'
    for path, selected in [(dev,rows[:2]),(test,rows[2:4])]:
        pd.DataFrame([{**row,'human_label':label} for row,label in zip(selected,['A','B'])]).to_csv(path,index=False)
        record_annotation_review(path,['Fixture Human A','Fixture Human B'])
    for name in ['stage1/best_model/topic_words.csv','stage1/best_model/classified_tweets.csv','stage2/topic_names.csv','stage3/theme_map.csv']:
        path=tmp_path/name;path.parent.mkdir(exist_ok=True,parents=True);path.write_text('fixture evidence',encoding='utf-8')
    codebook=tmp_path/'codebook.json'
    codebook.write_text(json.dumps({'themes':{'A':'Even numbers','B':'Odd numbers'},'decision_rule':'Use the final digit.'}),encoding='utf-8')
    cfg=PipelineConfig(input_csv=str(corpus),output_dir=str(tmp_path),themes=['A','B'],
        codebook_path=str(codebook),development_csv=str(dev),benchmark_csv=str(test),llm_backend='mock')
    for path in [dev,test]:record_annotation_review(path,['Fixture Human A','Fixture Human B'],cfg)
    record_human_review(cfg,['Fixture Human A','Fixture Human B'])
    monkeypatch.setattr('stage4_classification.build_theme_dictionaries',lambda cfg:{'A':{'even'},'B':{'odd'}})
    class Backend:
        name='test-fixture';model_id='MOCK';budget=None
        def complete(self,system,user,*args,**kwargs):
            text=kwargs['task_data']['text']
            return 'A' if int(text[-1])%2==0 else 'B'
    monkeypatch.setattr('llm_backend.make_backend',lambda cfg:Backend())
    return cfg


def test_phases_stop_before_scaling_and_require_actual_acceptance(tmp_path,monkeypatch):
    cfg=fixture(tmp_path,monkeypatch)
    run_validated_stage4(cfg)
    assert not (tmp_path/'stage4/validate_predictions.csv').exists()
    assert not (tmp_path/'stage4/classified_corpus.csv').exists()
    cfg.stage4_action='validate'
    run_validated_stage4(cfg)
    report=json.loads((tmp_path/'stage4/validation_report.json').read_text())
    assert report['gate_passed']
    cfg.stage4_action='classify'
    with pytest.raises(ValueError,match='inspect and approve'):run_validated_stage4(cfg)
    record_validation_review(cfg,['Fixture Human A','Fixture Human B'])
    run_validated_stage4(cfg)
    assert len(pd.read_csv(tmp_path/'stage4/classified_corpus.csv'))==6


def test_holdout_cannot_reselect_a_better_classifier(tmp_path,monkeypatch):
    cfg=fixture(tmp_path,monkeypatch)
    run_validated_stage4(cfg)
    cfg.stage4_action='validate'
    monkeypatch.setattr('stage4_classification.classify_text',lambda *a,**k:('A','matched','A'))
    # Boolean would be perfect on the held-out rows, but the frozen LLM must fail.
    monkeypatch.setattr('stage4_classification.boolean_classify',lambda text,*a:'A' if text.endswith('2') else 'B')
    with pytest.raises(RuntimeError,match='evaluation failed'):run_validated_stage4(cfg)
    report=json.loads((tmp_path/'stage4/validation_report.json').read_text())
    assert report['winner']=='llm' and report['metrics']['agreement']==0.5


def test_edited_evaluation_annotations_invalidate_acceptance(tmp_path,monkeypatch):
    from research_validation import require_validation_review
    cfg=fixture(tmp_path,monkeypatch)
    run_validated_stage4(cfg)
    cfg.stage4_action='validate';run_validated_stage4(cfg)
    record_validation_review(cfg,['Fixture Human A','Fixture Human B'])
    path=Path(cfg.benchmark_csv)
    path.write_text(path.read_text(encoding='utf-8')+'\n',encoding='utf-8')
    with pytest.raises(ValueError,match='evaluation annotations changed'):require_validation_review(cfg)


def test_edited_codebook_invalidates_review(tmp_path,monkeypatch):
    cfg=fixture(tmp_path,monkeypatch)
    Path(cfg.codebook_path).write_text('{}',encoding='utf-8')
    with pytest.raises(ValueError,match='stale'):run_validated_stage4(cfg)


def test_annotations_cannot_change_after_attestation(tmp_path,monkeypatch):
    cfg=fixture(tmp_path,monkeypatch)
    Path(cfg.development_csv).write_text(Path(cfg.development_csv).read_text()+'\n',encoding='utf-8')
    with pytest.raises(ValueError,match='stale'):run_validated_stage4(cfg)


def test_sample_substitution_is_rejected_before_model_calls(tmp_path,monkeypatch):
    from sampling import read_selected
    cfg=fixture(tmp_path,monkeypatch)
    _,sampling=read_selected(cfg,'target')
    manifest=tmp_path/'sampling_manifest.json'
    manifest.write_text(json.dumps({'sampling':sampling,'packets':{
        'development':{'ids':['0','4']},'evaluation':{'ids':['2','3']}}}),encoding='utf-8')
    cfg.annotation_manifest=str(manifest)
    with pytest.raises(ValueError,match='frozen sampling manifest'):run_validated_stage4(cfg)


def test_independent_names_must_match_actual_attestation(tmp_path,monkeypatch):
    cfg=fixture(tmp_path,monkeypatch)
    frame=pd.read_csv(cfg.development_csv,dtype=str)
    frame['reviewer_1']='Fixture Human A'
    frame['reviewer_2']='Unattested reviewer'
    frame['reviewer_1_label']=frame.human_label
    frame['reviewer_2_label']=frame.human_label
    frame.to_csv(cfg.development_csv,index=False)
    record_annotation_review(cfg.development_csv,['Fixture Human A','Fixture Human B'],cfg)
    with pytest.raises(ValueError,match='reviewer names'):run_validated_stage4(cfg)


def failed_demo_fixture(tmp_path,monkeypatch):
    from research_validation import validation_spec
    from provenance import fingerprint
    from review import sha
    from sampling import read_selected
    cfg=fixture(tmp_path,monkeypatch);run_validated_stage4(cfg)
    cfg.stage4_action='validate'
    monkeypatch.setattr('stage4_classification.classify_text',lambda *a,**k:('A','matched','A'))
    with pytest.raises(RuntimeError,match='evaluation failed'):run_validated_stage4(cfg)
    cfg.api_budget_usd=150;cfg.demonstration_exception_path=str(tmp_path/'exception.json')
    root=tmp_path/'stage4'
    record={'decision':'continue_unvalidated_demonstration','classifier_validated':False,
        'validation_report_sha256':sha(root/'validation_report.json'),
        'classifier_selection_sha256':sha(root/'classifier_selection.json'),
        'benchmark_sha256':sha(cfg.benchmark_csv),'specification_sha256':fingerprint(validation_spec(cfg)),
        'target_selection':read_selected(cfg,'target')[1],'reporting':'unvalidated model-assigned shares',
        'researcher':'Fixture investigator','rationale':'Artificial test of explicit exception, not research approval.',
        'recorded_at':'2026-11-19T00:00:00Z','cumulative_budget_usd':150}
    Path(cfg.demonstration_exception_path).write_text(json.dumps(record),encoding='utf-8')
    cfg.stage4_action='classify'
    return cfg


def test_explicit_exception_preserves_failed_gate_and_unvalidated_output(tmp_path,monkeypatch):
    from stage5_inference import run_stage5
    cfg=failed_demo_fixture(tmp_path,monkeypatch)
    with pytest.raises(ValueError,match='passing held-out'):record_validation_review(cfg,['Fixture Human A','Fixture Human B'])
    run_validated_stage4(cfg);run_stage5(cfg)
    assert not json.loads((tmp_path/'stage4/validation_report.json').read_text())['gate_passed']
    assert not json.loads((tmp_path/'stage4/classification_status.json').read_text())['classifier_validated']
    assert not json.loads((tmp_path/'stage5/estimand.json').read_text())['classifier_validated']
    assert not (tmp_path/'stage4/validation_review.json').exists()
    assert pd.read_csv(tmp_path/'stage5/theme_counts.csv').documents.sum()==6


@pytest.mark.parametrize('change',['budget','prompt','annotations','target','validated','tests'])
def test_demonstration_exception_rejects_changed_scope_before_paid_backend(tmp_path,monkeypatch,change):
    cfg=failed_demo_fixture(tmp_path,monkeypatch)
    def forbidden(*args):raise AssertionError('Backend must not open before the exception is checked.')
    monkeypatch.setattr('llm_backend.make_backend',forbidden)
    if change=='budget':cfg.api_budget_usd=151
    elif change=='prompt':cfg.classify_temperature=.7
    elif change=='annotations':Path(cfg.benchmark_csv).write_text(Path(cfg.benchmark_csv).read_text()+'\n')
    elif change=='target':cfg.target_window=['2019-01-01','2019-12-31']
    elif change=='tests':cfg.run_pairwise_tests=True
    else:
        path=Path(cfg.demonstration_exception_path);r=json.loads(path.read_text());r['classifier_validated']=True;path.write_text(json.dumps(r))
    with pytest.raises(ValueError):run_validated_stage4(cfg)
