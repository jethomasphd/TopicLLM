import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pytest
from config import PipelineConfig
from api_budget import ApiBudget, BudgetExceeded, request_fingerprint
from llm_backend import LLMBackend
from review import require_review, record_human_review
from trump import quickcheck


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


def test_mock_or_oracle_review_cannot_authorize_research(tmp_path):
    cfg=review_fixture(tmp_path)
    record=record_human_review(cfg,['Fixture Researcher A','Fixture Researcher B'])
    record.update(review_mode='synthetic-oracle',human_review_performed=False)
    (tmp_path/'stage3/review_record.json').write_text(json.dumps(record),encoding='utf-8')
    with pytest.raises(ValueError,match='two-researcher'):require_review(cfg)


def test_offline_quickcheck_verifies_the_single_corpus(tmp_path):
    report=quickcheck(PipelineConfig(output_dir=str(tmp_path)))
    assert report['records']==34416 and report['api_calls']==0
    assert report['window']==['2015-06-16','2021-01-08']


@pytest.mark.parametrize('names', [['Same Person',' same person '], ['', 'Researcher B'], ['agent','Researcher B']])
def test_external_review_records_require_distinct_nonblank_names(tmp_path, names):
    cfg=review_fixture(tmp_path)
    record=record_human_review(cfg,['Fixture Researcher A','Fixture Researcher B'])
    record['reviewers']=names
    (tmp_path/'stage3/review_record.json').write_text(json.dumps(record),encoding='utf-8')
    with pytest.raises(ValueError,match='two-researcher'):require_review(cfg)


def test_bundled_provenance_uses_declared_hashes_not_a_self_comparison(tmp_path,monkeypatch):
    import config,shutil
    from provenance import input_kind
    source=Path(config.DEMO_DIR)/'trump'
    (tmp_path/'trump').mkdir()
    for name in ('manifest.json','corpus.csv'):shutil.copyfile(source/name,tmp_path/'trump'/name)
    monkeypatch.setattr(config,'DEMO_DIR',str(tmp_path))
    path=tmp_path/'trump/corpus.csv'
    assert input_kind(path,path.name)=='public-trump-tutorial'
    path.write_bytes(path.read_bytes()+b'\n')
    assert input_kind(path,path.name)=='researcher-supplied-unverified'


def test_cli_refuses_unbudgeted_paid_stages_before_execution(monkeypatch):
    import run_pipeline,sys
    monkeypatch.setattr(run_pipeline,'CONFIG',PipelineConfig())
    monkeypatch.setattr(sys,'argv',['topicllm','--profile','research','--stages','2,3'])
    with pytest.raises(SystemExit) as error:run_pipeline.main()
    assert error.value.code==2


def test_quickcheck_plan_has_zero_calls(monkeypatch,capsys):
    import run_pipeline,sys
    monkeypatch.setattr(run_pipeline,'CONFIG',PipelineConfig())
    monkeypatch.setattr(sys,'argv',['topicllm','--profile','quickcheck','--plan'])
    run_pipeline.main();plan=json.loads(capsys.readouterr().out)
    assert plan['stages']==[]
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


def test_failed_response_preserves_known_usage_without_caching_a_label(tmp_path):
    cfg=PipelineConfig(output_dir=str(tmp_path),api_budget_usd=.01)
    budget=ApiBudget(cfg)
    key='truncated-fixture'
    call=budget.reserve(key,'digest','system','user',32)
    budget.settle(call,key,'digest',result={'raw_text':'Unfinished', 'finish_reason':'length',
        'usage':{'prompt_tokens':10,'completion_tokens':32}},error='IncompleteResponse')
    assert budget.cached(key,'digest') is None
    report=budget.export()
    assert report['successful_calls']==0
    assert report['conservatively_accounted_usd']==.000345
    assert json.loads((tmp_path/'api_responses.json').read_text())[0]['response']['raw_text']=='Unfinished'


def test_campaign_profile_supplies_declared_naming_settings_without_overriding_votes(tmp_path,monkeypatch,capsys):
    import run_pipeline,sys
    for extra,expected in [([],500),(['--votes','3'],3)]:
        cfg=PipelineConfig(output_dir=str(tmp_path))
        monkeypatch.setattr(run_pipeline,'CONFIG',cfg)
        monkeypatch.setattr(sys,'argv',['topicllm','--profile','trump-demo','--stages','2','--plan',*extra])
        run_pipeline.main()
        assert json.loads(capsys.readouterr().out)['naming_calls']==25*expected
        assert cfg.naming_max_tokens==32
        assert cfg.votes_per_topic==expected
        assert '2015-2016' in cfg.domain_context


def test_direct_sdk_truncation_retains_usage_and_never_becomes_a_ballot(tmp_path):
    from types import SimpleNamespace
    from llm_backend import OpenAIBackend, LLMBackend, ERROR_LABEL
    cfg=PipelineConfig(output_dir=str(tmp_path),api_budget_usd=.01,max_retries=1)
    backend=OpenAIBackend.__new__(OpenAIBackend);LLMBackend.__init__(backend,cfg)
    response=SimpleNamespace(model=cfg.llm_model,_request_id='fixture-request',system_fingerprint='fixture',
        choices=[SimpleNamespace(finish_reason='length',message=SimpleNamespace(content='Unfinished proposal'))],
        usage=SimpleNamespace(model_dump=lambda:{'prompt_tokens':10,'completion_tokens':32}))
    backend.client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kwargs:response)))
    assert backend.complete('system','user',32,.5,request_key='incomplete-fixture')==ERROR_LABEL
    report=backend.budget.export()
    assert report['failed_calls']==1 and report['unsettled_calls']==0
    assert report['conservatively_accounted_usd']==.000345
    entry=json.loads((tmp_path/'api_responses.json').read_text())[0]
    assert entry['response']['finish_reason']=='length'
    assert entry['response']['raw_text']=='Unfinished proposal'


def test_invalid_classification_retries_are_bounded_preserved_and_resumable(tmp_path):
    from llm_backend import LLMBackend
    from stage4_classification import classify_text
    class ScriptedBackend(LLMBackend):
        name='openai'
        def __init__(self, cfg, answers):
            super().__init__(cfg); self.answers=iter(answers); self.calls=0
        def _complete(self, *args):
            self.calls+=1
            return {'text':next(self.answers),'usage':{'prompt_tokens':10,'completion_tokens':3}}
    cfg=PipelineConfig(output_dir=str(tmp_path/'recovered'),themes=['A','B'],api_budget_usd=.1,max_retries=2)
    backend=ScriptedBackend(cfg,['A or B','A'])
    assert classify_text(backend,'fixture',cfg,request_key='post:1')==('A','matched','A')
    assert classify_text(backend,'fixture',cfg,request_key='post:1')==('A','matched','A')
    assert backend.calls==2
    backend.budget.export()
    evidence=json.loads((tmp_path/'recovered/api_responses.json').read_text())
    assert [row['response']['text'] for row in evidence]==['A or B','A']
    cfg.output_dir=str(tmp_path/'unresolved')
    failed=ScriptedBackend(cfg,['A or B','Neither option is clear'])
    assert classify_text(failed,'fixture',cfg,request_key='post:2')[1]=='unmatched'
    assert classify_text(failed,'fixture',cfg,request_key='post:2')[1]=='unmatched'
    assert failed.calls==2


def test_package_can_export_effective_configuration_without_overwriting(tmp_path, monkeypatch):
    import run_pipeline, sys
    path=tmp_path/'research.json'
    monkeypatch.setattr(run_pipeline,'CONFIG',PipelineConfig())
    monkeypatch.setattr(sys,'argv',['topicllm','--profile','trump-demo','--write-config',str(path)])
    run_pipeline.main()
    config=json.loads(path.read_text(encoding='utf-8'))
    assert config['discovery_window']==['2015-06-16','2016-11-08']
    assert config['target_window']==['2017-01-20','2021-01-08']
    assert config['votes_per_topic']==500 and config['naming_max_tokens']==32
    assert config['api_budget_usd'] is None
    before=path.read_bytes()
    with pytest.raises(SystemExit):run_pipeline.main()
    assert path.read_bytes()==before
