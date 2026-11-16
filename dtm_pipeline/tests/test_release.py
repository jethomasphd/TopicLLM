import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pytest
from config import PipelineConfig
from api_budget import ApiBudget, BudgetExceeded, request_fingerprint
from llm_backend import LLMBackend
from review import require_review, record_human_review, exact_synthetic_inputs
from synthetic_workflow import quickcheck


def test_concurrent_calls_cannot_overrun_budget(tmp_path):
    cfg=PipelineConfig(output_dir=str(tmp_path),api_budget_usd=.001)
    budget=ApiBudget(cfg)
    def reserve(i):
        try:return budget.reserve(str(i),'f','s','u',1)
        except BudgetExceeded:return None
    with ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(reserve,range(20)))
    assert sum(r is not None for r in results)==1
    assert budget.export()['conservatively_accounted_usd']<=.001


def test_paid_cache_resumes_without_recharging_and_rejects_changed_prompt(tmp_path):
    cfg=PipelineConfig(output_dir=str(tmp_path),api_budget_usd=.01,max_retries=1)
    class Provider(LLMBackend):
        name='openai'
        def _complete(self,*args):return {'text':'Gaming','usage':{'prompt_tokens':10,'completion_tokens':1},'model':cfg.llm_model}
    backend=Provider(cfg)
    first=backend.complete('s','u',15,.5,request_key='benchmark:1')
    assert backend.complete('s','u',15,.5,request_key='benchmark:1')==first
    assert backend.budget.export()['attempted_calls']==1
    with pytest.raises(ValueError,match='changed inputs'):
        backend.complete('s','different',15,.5,request_key='benchmark:1')


def test_quota_failure_is_not_retried_or_cached_as_a_vote(tmp_path):
    cfg=PipelineConfig(output_dir=str(tmp_path),api_budget_usd=.01,max_retries=5)
    class Failure(Exception):retryable=False
    class Provider(LLMBackend):
        name='openai'
        def _complete(self,*args):raise Failure()
    backend=Provider(cfg)
    assert backend.complete('s','u',15,.5,request_key='benchmark:1')=='__API_ERROR__'
    assert backend.budget.export()['attempted_calls']==1


def review_fixture(tmp_path):
    corpus=tmp_path/'input.csv';corpus.write_text('post_id,tweet\n1,example\n',encoding='utf-8')
    benchmark=tmp_path/'benchmark.csv';benchmark.write_text('tweet,human_label\nexample,Sports\n',encoding='utf-8')
    for name in ['stage1/best_model/topic_words.csv','stage1/best_model/classified_tweets.csv','stage2/topic_names.csv','stage3/theme_map.csv']:
        path=tmp_path/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('test fixture\n',encoding='utf-8')
    return PipelineConfig(input_csv=str(corpus),benchmark_csv=str(benchmark),output_dir=str(tmp_path))


def test_research_requires_current_evidence_bound_human_attestation(tmp_path):
    cfg=review_fixture(tmp_path)
    with pytest.raises(ValueError,match='review_record'):require_review(cfg)
    record_human_review(cfg,['Fixture Researcher A','Fixture Researcher B'])
    assert require_review(cfg)['human_review_performed']
    (tmp_path/'stage3/theme_map.csv').write_text('changed mapping\n')
    with pytest.raises(ValueError,match='stale'):require_review(cfg)


def test_synthetic_review_and_benchmark_cannot_authorize_research(tmp_path):
    cfg=review_fixture(tmp_path)
    record_human_review(cfg,['Fixture Researcher A','Fixture Researcher B'])
    cfg.benchmark_csv=PipelineConfig().benchmark_csv
    with pytest.raises(ValueError,match='bundled synthetic benchmark'):require_review(cfg)
    with pytest.raises(ValueError,match='exact bundled'):exact_synthetic_inputs(cfg)


def test_offline_quickcheck_exercises_real_inference(tmp_path):
    report=quickcheck(PipelineConfig(output_dir=str(tmp_path)))
    assert report['records']==5872 and report['comparisons']==15
    assert all(row['computed']==row['reported'] for row in report['prevalence_comparison'])
    assert not report['human_validation'] and not report['historical_recomputation']


@pytest.mark.parametrize('names', [['Same Person',' same person '], ['', 'Researcher B'], ['agent','Researcher B']])
def test_external_review_records_require_distinct_nonblank_names(tmp_path, names):
    cfg=review_fixture(tmp_path)
    record=record_human_review(cfg,['Fixture Researcher A','Fixture Researcher B'])
    record['reviewers']=names
    (tmp_path/'stage3/review_record.json').write_text(json.dumps(record),encoding='utf-8')
    with pytest.raises(ValueError,match='two-researcher'):require_review(cfg)


def test_synthetic_fixture_rejects_changed_inference_design():
    cfg=PipelineConfig();cfg.themes=['Unrelated theme']
    with pytest.raises(ValueError,match='taxonomy'):exact_synthetic_inputs(cfg)


def test_bundled_provenance_uses_declared_hashes_not_a_self_comparison(tmp_path,monkeypatch):
    import config,shutil
    from provenance import input_kind
    source=Path(config.DEMO_DIR)
    for name in ('synthetic-integrity.json','demonstration_corpus.csv'):shutil.copyfile(source/name,tmp_path/name)
    monkeypatch.setattr(config,'DEMO_DIR',str(tmp_path))
    path=tmp_path/'demonstration_corpus.csv'
    assert input_kind(path,path.name)=='bundled-synthetic'
    path.write_bytes(path.read_bytes()+b'\n')
    assert input_kind(path,path.name)=='researcher-supplied-unverified'


def test_cli_refuses_unbudgeted_synthetic_run_before_discovery(monkeypatch):
    import run_pipeline,sys
    monkeypatch.setattr(run_pipeline,'CONFIG',PipelineConfig())
    monkeypatch.setattr(sys,'argv',['topicllm','--profile','synthetic-e2e'])
    with pytest.raises(SystemExit) as error:run_pipeline.main()
    assert error.value.code==2


def test_quickcheck_plan_has_zero_calls(monkeypatch,capsys):
    import run_pipeline,sys
    monkeypatch.setattr(run_pipeline,'CONFIG',PipelineConfig())
    monkeypatch.setattr(sys,'argv',['topicllm','--profile','quickcheck','--plan'])
    run_pipeline.main();plan=json.loads(capsys.readouterr().out)
    assert plan['stages']==[5]
    assert plan['naming_calls']==plan['benchmark_calls']==plan['maximum_corpus_calls']==0


def test_real_openai_sdk_request_and_response_contract(tmp_path,monkeypatch):
    import openai
    from openai import _base_client
    httpx = getattr(_base_client, 'httpx2', None) or _base_client.httpx
    from llm_backend import OpenAIBackend
    monkeypatch.setenv('OPENAI_API_KEY','test-fixture-only')
    cfg=PipelineConfig(output_dir=str(tmp_path),api_budget_usd=.01,max_retries=1)
    backend=OpenAIBackend(cfg);backend.client.close()
    calls=[]
    def transport(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200,headers={'x-request-id':'fixture-request'},json={
            'id':'fixture','object':'chat.completion','created':0,'model':cfg.llm_model,'system_fingerprint':'fixture',
            'choices':[{'index':0,'finish_reason':'stop','message':{'role':'assistant','content':'Gaming'}}],
            'usage':{'prompt_tokens':10,'completion_tokens':1,'total_tokens':11}})
    backend.client=openai.OpenAI(api_key='test-fixture-only',max_retries=0,http_client=httpx.Client(transport=httpx.MockTransport(transport)))
    try:
        assert backend.complete('system','user',120,.5,request_key='sdk-contract')=='Gaming'
        assert calls==[{'model':cfg.llm_model,'messages':[{'role':'system','content':'system'},{'role':'user','content':'user'}],'max_tokens':120,'temperature':.5,'n':1,'store':False}]
        assert backend.budget.export()['conservatively_accounted_usd']==.000035
        records=json.loads((tmp_path/'api_responses.json').read_text())
        assert records[0]['response']['request_id']=='fixture-request'
    finally:backend.client.close()
