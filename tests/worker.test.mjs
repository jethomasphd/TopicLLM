import test from 'node:test';
import assert from 'node:assert/strict';
import worker,{validateCall} from '../worker/index.js';
const env={OPENAI_API_KEY:'test-provider-secret',RESEARCH_ACCESS_TOKEN:'research-code',OPENAI_MODEL:'test-model',RATE_LIMITER:{limit:async()=>({success:true})},ASSETS:{fetch:async()=>new Response('asset')}};
const req=(data={},headers={})=>new Request('https://example.org/api/llm',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer research-code',Origin:'https://example.org',...headers},body:JSON.stringify(data)});
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
test('gateway returns model provenance but never provider secrets',async()=>{
  const previous=globalThis.fetch;
  try{
    globalThis.fetch=async(url,options)=>{
      assert.equal(url,'https://api.openai.com/v1/chat/completions');
      const data=JSON.parse(options.body);assert.equal(data.model,'test-model');assert.equal(data.store,false);
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
