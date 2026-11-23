import test from 'node:test';
import assert from 'node:assert/strict';
import worker,{validateCall} from '../worker/index.js';
import {classificationResult} from '../worker/provider.js';
import {environment} from './quota-fixture.mjs';
const env=environment();
const req=(data={},headers={})=>new Request('https://example.org/api/llm',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer research-code',Origin:'https://example.org',...headers},body:JSON.stringify(data)});
test('public navigation uses the HTTPS primary domain and preserves paths and queries',async()=>{
  for(const host of ['www.topicllm.dev','topicllm.jethomasphd.workers.dev']){
    const result=await worker.fetch(new Request(`https://${host}/paper/?view=inference`),{});
    assert.equal(result.status,308);
    assert.equal(result.headers.get('Location'),'https://topicllm.dev/paper/?view=inference');
    // A retired page reaches its new home on the primary domain in one permanent hop.
    const moved=await worker.fetch(new Request(`https://${host}/app/?view=inference`),{});
    assert.equal(moved.status,301);
    assert.equal(moved.headers.get('Location'),'https://topicllm.dev/tutorial/?view=inference');
  }
  const assets={ASSETS:{fetch:async()=>new Response('asset')}};
  for(const host of ['topicllm.dev','localhost:8787','unrelated.example']){
    const result=await worker.fetch(new Request(`https://${host}/tutorial/`),assets);
    assert.equal(await result.text(),'asset');
  }
  const secure=await worker.fetch(new Request('http://topicllm.dev/paper/'),{});
  assert.equal(secure.status,308);assert.equal(secure.headers.get('Location'),'https://topicllm.dev/paper/');
  const movedSecure=await worker.fetch(new Request('http://topicllm.dev/reproduce/'),{});
  assert.equal(movedSecure.status,301);assert.equal(movedSecure.headers.get('Location'),'https://topicllm.dev/use/');
});
const movedPages={'/app':'/tutorial/','/data':'/tutorial/#dataset','/validation':'/tutorial/#check','/reproduce':'/use/','/audit':'/research/','/welcome':'/research/#author','/guide':'/#ask'};
test('retired pages redirect permanently with or without a trailing slash or index.html',async()=>{
  const assets={ASSETS:{fetch(){throw new Error('A retired page reached asset storage');}}};
  for(const [page,target] of Object.entries(movedPages)){
    const [path,fragment]=target.split('#'),hash=fragment?'#'+fragment:'';
    for(const variant of [page,page+'/',page+'/index.html']){
      for(const method of ['GET','HEAD']){
        const response=await worker.fetch(new Request('https://topicllm.dev'+variant,{method}),assets);
        assert.equal(response.status,301,`${method} ${variant}`);
        assert.equal(response.headers.get('Location'),'https://topicllm.dev'+path+hash,variant);
      }
      const query=await worker.fetch(new Request('https://topicllm.dev'+variant+'?ref=old&x=1'),assets);
      assert.equal(query.headers.get('Location'),'https://topicllm.dev'+path+'?ref=old&x=1'+hash,variant+' with query');
    }
    // Local previews keep their own origin.
    const local=await worker.fetch(new Request('http://localhost:8787'+page+'/'),assets);
    assert.equal(local.status,301);assert.equal(local.headers.get('Location'),'http://localhost:8787'+path+hash);
  }
});
test('redirects leave data files, new pages, non-navigation methods and withdrawn assets alone',async()=>{
  const served=[];const assets={ASSETS:{fetch:async request=>{served.push(new URL(request.url).pathname);return new Response('asset');}}};
  const kept=['/data/trump/corpus.csv','/data/trump/manifest.json','/data/README.md','/guide/knowledge.md','/','/tutorial/','/use/','/research/','/paper/','/privacy/','/studies/1/','/studies/2/','/application/','/data.csv','/datasets/'];
  for(const path of kept){
    const response=await worker.fetch(new Request('https://topicllm.dev'+path),assets);
    assert.equal(response.status,200,path);assert.equal(response.headers.get('Location'),null,path);
  }
  assert.deepEqual(served,kept);
  const post=await worker.fetch(new Request('https://topicllm.dev/app/',{method:'POST'}),assets);
  assert.equal(post.status,200);assert.equal(post.headers.get('Location'),null);
  for(const path of ['/validation/results.json','/validation/synthetic-results.json','/data/trump/campaign/evaluation_annotations.csv'])
    assert.equal((await worker.fetch(new Request('https://topicllm.dev'+path),assets)).status,410,path);
});
test('domain migration keeps API requests on their original origin',async()=>{
  const config=await worker.fetch(new Request('https://www.topicllm.dev/api/config'),env);
  assert.equal(config.status,200);assert.equal(config.headers.get('Location'),null);
  const blocked=await worker.fetch(new Request('https://www.topicllm.dev/api/demo',{method:'POST',headers:{Origin:'https://topicllm.dev'}}),env);
  assert.equal(blocked.status,403);
});
test('local preview can disable canonical redirects without affecting production defaults',async()=>{
  const response=await worker.fetch(new Request('http://topicllm.dev/'),{CANONICAL_REDIRECTS:'false',ASSETS:{fetch:async()=>new Response('local preview')}});
  assert.equal(response.status,200);assert.equal(await response.text(),'local preview');
});
test('gateway fails closed without configuration',async()=>assert.equal((await worker.fetch(req(),{})).status,503));
test('gateway rejects missing credentials and cross-origin callers',async()=>{
  assert.equal((await worker.fetch(req({}, {Authorization:'Bearer wrong'}),env)).status,401);
  assert.equal((await worker.fetch(req({}, {Origin:'https://evil.example'}),env)).status,403);
});
test('gateway caps input and rate before contacting OpenAI',async()=>{
  assert.equal((await worker.fetch(req({task:'other'}),env)).status,400);
  assert.equal((await worker.fetch(req({text:'x'.repeat(25000)}),env)).status,413);
  assert.equal((await worker.fetch(req(),{...env,RATE_LIMITER:{limit:async()=>({success:false})}})).status,429);
});
test('classification theme limits and token budget are server controlled',()=>{
  assert.throws(()=>validateCall({task:'classify',text:'abc',themes:['Sports','Sports']}));
  const call=validateCall({task:'classify',text:'abc',themes:['Sports'],model:'attacker-model',max_tokens:100000});
  assert.equal(call.max_tokens,120);
});

test('classification accepts one allowed choice and retains the raw response',()=>{
  const call=validateCall({task:'classify',text:'A public post',themes:['Policy','Elections']});
  for(const raw of ['Policy','1','1. Policy','Theme: Policy','"policy."']){
    const result=classificationResult({text:raw},call);
    assert.equal(result.text,'Policy');assert.equal(result.raw_text,raw);
  }
  for(const text of ['Policy and Elections','1, 2','A new category','4',''])assert.throws(()=>classificationResult({text},call));
});
test('gateway returns model provenance but never provider secrets',async()=>{
  const previous=globalThis.fetch;
  try{
    globalThis.fetch=async(url,options)=>{
      assert.equal(url,'https://api.openai.com/v1/chat/completions');
      const data=JSON.parse(options.body);assert.equal(data.model,'gpt-4o-2024-08-06');assert.equal(data.store,false);
      return Response.json({model:'test-model-snapshot',choices:[{finish_reason:'stop',message:{content:'Sports'}}],usage:{total_tokens:40}}, {headers:{'x-request-id':'req-test'}});
    };
    const r=await worker.fetch(req({task:'classify',text:'a sports post',themes:['Sports']}),env);
    assert.equal(r.status,200);const data=await r.json();assert.equal(data.request_id,'req-test');assert.equal(data.model,'test-model-snapshot');assert.ok(!JSON.stringify(data).includes('test-provider-secret'));
  }finally{globalThis.fetch=previous;}
});
test('truncated model responses cannot enter the analysis',async()=>{
  const previous=globalThis.fetch;
  try{globalThis.fetch=async()=>Response.json({choices:[{finish_reason:'length',message:{content:'Sports'}}]});
    assert.equal((await worker.fetch(req({task:'name',words:'a,b',domain:'posts'}),env)).status,502);
  }finally{globalThis.fetch=previous;}
});

test('provider quota failures are actionable, sanitized and never retried',async()=>{
  const previous=globalThis.fetch;
  try {
    for (const code of ['insufficient_quota','credit_balance_exhausted','organization_usage_limit_exceeded','organization_spend_limit_exceeded','project_spend_limit_exceeded']) {
      globalThis.fetch=async()=>Response.json({error:{code,type:'insufficient_quota',message:'private-provider-detail'}},{status:429,headers:{'x-request-id':'req-quota'}});
      const response=await worker.fetch(req({task:'name',words:'a,b',domain:'posts'}),env), data=await response.json();
      assert.equal(response.status,429); assert.equal(data.code,code); assert.equal(data.retryable,false); assert.equal(data.request_id,'req-quota');
      assert.ok(!JSON.stringify(data).includes('private-provider-detail'));
    }
  } finally { globalThis.fetch=previous; }
});

test('temporary provider rate limits retain bounded retry guidance',async()=>{
  const previous=globalThis.fetch;
  try {
    globalThis.fetch=async()=>Response.json({error:{code:'rate_limit_exceeded'}},{status:429,headers:{'Retry-After':'12'}});
    const response=await worker.fetch(req({task:'name',words:'a,b',domain:'posts'}),env);
    assert.equal(response.headers.get('Retry-After'),'12'); assert.equal((await response.json()).retryable,true);
  } finally { globalThis.fetch=previous; }
});
