from pathlib import Path
import json,shutil
import pytest
from config import PipelineConfig, DEMO_DIR
from study1 import verify_study1
from provenance import input_kind

def test_original_cohort_reconstructs_and_is_the_default():
    report=verify_study1()
    assert report['cohort_reconstructed']
    assert report['counts']==dict(collected=6174,full=5872,brands=11,blank_text=1,analysis_nonempty=5871,discovery=704)
    cfg=PipelineConfig()
    assert Path(cfg.discovery_input_csv).name=='discovery.csv'
    assert Path(cfg.input_csv).name=='analysis.csv'
    assert input_kind(cfg.input_csv,'demonstration_corpus.csv')=='released-study1'
    assert cfg.benchmark_csv=='human_labels.csv'

def test_study1_modified_input_is_rejected(tmp_path):
    shutil.copytree(Path(DEMO_DIR)/'study1',tmp_path/'data')
    path=tmp_path/'data'/'discovery.csv';path.write_bytes(path.read_bytes()+b'\n')
    with pytest.raises(ValueError,match='checksum mismatch'):verify_study1(tmp_path/'data')

def test_custom_corpus_does_not_silently_use_study1_discovery():
    cfg=PipelineConfig(input_csv='my-corpus.csv')
    assert cfg.discovery_input_csv is None
    cfg=PipelineConfig(input_csv='my-corpus.csv',discovery_input_csv='my-subset.csv')
    assert cfg.discovery_input_csv=='my-subset.csv'

def test_default_demo_plan_runs_discovery_without_paid_stages(monkeypatch,capsys):
    import run_pipeline,sys
    monkeypatch.setattr(run_pipeline,'CONFIG',PipelineConfig())
    monkeypatch.setattr(sys,'argv',['topicllm','--profile','study1-demo','--plan'])
    run_pipeline.main();plan=json.loads(capsys.readouterr().out)
    assert plan['stages']==[1] and plan['discovery_candidates']==1200
    assert plan['naming_calls']==plan['benchmark_calls']==plan['maximum_corpus_calls']==0

def test_custom_cli_input_clears_default_discovery(monkeypatch,capsys):
    import run_pipeline,sys
    monkeypatch.setattr(run_pipeline,'CONFIG',PipelineConfig())
    monkeypatch.setattr(sys,'argv',['topicllm','--input','custom.csv','--plan'])
    run_pipeline.main();plan=json.loads(capsys.readouterr().out)
    assert plan['discovery_input']==plan['analysis_input']=='custom.csv'
