import sys
from pathlib import Path
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from config import PipelineConfig
from stage4_classification import canonicalize, INVALID_LABEL, classify_corpus, score_labels
from llm_backend import MockBackend
from stage5_inference import run_stage5

@pytest.mark.parametrize('raw',['Not Sports','Sports or Gaming','I cannot classify this',''])
def test_ambiguous_replies_are_not_measurements(raw):
    assert canonicalize(raw)[0] == INVALID_LABEL

def test_checkpoint_rejects_reordered_corpus(tmp_path):
    cfg=PipelineConfig(output_dir=str(tmp_path))
    corpus=pd.DataFrame({'tweet':['sport sport','restaurant support']})
    classify_corpus(MockBackend(cfg),corpus,str(tmp_path),cfg)
    with pytest.raises(ValueError,match='changed'):
        classify_corpus(MockBackend(cfg),corpus.iloc[::-1],str(tmp_path),cfg)

def test_checkpoint_rejects_changed_taxonomy(tmp_path):
    cfg=PipelineConfig(output_dir=str(tmp_path))
    corpus=pd.DataFrame({'tweet':['sport sport']})
    classify_corpus(MockBackend(cfg),corpus,str(tmp_path),cfg)
    cfg.themes=['A different theme']
    with pytest.raises(ValueError,match='changed'):
        classify_corpus(MockBackend(cfg),corpus,str(tmp_path),cfg)

def test_empty_benchmark_is_rejected():
    with pytest.raises(ValueError,match='non-empty'):
        score_labels(pd.Series(dtype=str),pd.Series(dtype=str),['Sports'])

def test_inference_refuses_unresolved_labels(tmp_path):
    (tmp_path/'stage4').mkdir()
    pd.DataFrame({'tweet':['unknown'],'date':['2020-01-01'],'theme':[INVALID_LABEL]}).to_csv(tmp_path/'stage4/classified_corpus.csv',index=False)
    with pytest.raises(ValueError,match='Resolve'):
        run_stage5(PipelineConfig(output_dir=str(tmp_path),themes=["Sports"]))

def test_failed_benchmark_retains_raw_responses(tmp_path, monkeypatch):
    import stage4_classification as stage4
    class BrokenBackend:
        name='test';model_id='test-no-network'
        def complete(self,*args,**kwargs):return '__API_ERROR__'
    benchmark=tmp_path/'benchmark.csv'
    pd.DataFrame({'tweet':['Example sports post'],'human_label':['Sports']}).to_csv(benchmark,index=False)
    monkeypatch.setattr(stage4,'make_backend',lambda cfg:BrokenBackend())
    monkeypatch.setattr(stage4,'build_theme_dictionaries',lambda cfg:{})
    monkeypatch.setattr('review.require_review',lambda cfg:{'review_mode':'test-fixture','human_review_performed':False})
    with pytest.raises(RuntimeError,match='benchmark calls failed'):
        stage4.run_stage4(PipelineConfig(output_dir=str(tmp_path),benchmark_csv=str(benchmark),themes=["Sports"],validation_mode="legacy-single-benchmark"))
    saved=pd.read_csv(tmp_path/'stage4/benchmark_predictions.csv')
    assert saved.llm_raw_response.tolist()==['__API_ERROR__']
