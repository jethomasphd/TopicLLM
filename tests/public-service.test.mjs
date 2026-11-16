import test from 'node:test';
import assert from 'node:assert/strict';
import worker,{demoCall} from '../worker/index.js';
import {environment} from './quota-fixture.mjs';
import {issueSession,session} from '../worker/session.js';
const reserve=(env,input)=>env.QUOTAS.get('x').fetch(new Request('https://quota/reserve',{method:'POST',body:JSON.stringify({scope:'public',session:'session1',ip:'ip1',fingerprint:'f',reserved:1000000,...input})}));
const settle=(env,key,extra={})=>env.QUOTAS.get('x').fetch(new Request('https://quota/settle',{method:'POST',body:JSON.stringify({key,ok:true,http_status:200,response:{text:'Gaming'},...extra})}));

test('public tasks reject arbitrary text, themes and unknown IDs',()=>{
  assert.throws(()=>demoCall({task:'classify',exampleId:'0',text:'private corpus'}));
  assert.throws(()=>demoCall({task:'name',topicId:'999'}));
  assert.equal(demoCall({task:'classify',exampleId:'4'}).task,'classify');
});
test('signed anonymous sessions cannot be forged or extended',async()=>{
  const env=environment(),cookie=await issueSession(env);
  const request=value=>new Request('https://example.org',{headers:{Cookie:'__Host-topicllm='+value}});
  assert.ok(await session(request(cookie),env));
  assert.equal(await session(request(cookie.slice(0,-1)+'x'),env),null);
  assert.equal(await session(request(cookie.replace(/\.\d+\./,'.9999999999.')),env),null);
});
test('atomic reservations cannot overspend under concurrent requests',async()=>{
  const env=environment({DEMO_DAILY_USD:'0.01',DEMO_MONTHLY_USD:'0.01'});
  const results=await Promise.all(Array.from({length:20},(_,i)=>reserve(env,{key:'k'+i,reserved:6000000})));
  assert.equal(results.filter(r=>r.status===200).length,1);
  assert.equal(results.filter(r=>r.status===429).length,19);
});
test('failed or uncertain provider calls keep their reservation',async()=>{
  const env=environment({DEMO_DAILY_USD:'0.001',DEMO_MONTHLY_USD:'0.001'});
  assert.equal((await reserve(env,{key:'first'})).status,200);
  await settle(env,'first',{ok:false,actual:null,http_status:504});
  assert.equal((await reserve(env,{key:'second'})).status,429);
});
test('completed retries are idempotent and altered payloads are rejected',async()=>{
  const env=environment();await reserve(env,{key:'first'});await settle(env,'first',{actual:1000});
  const duplicate=await (await reserve(env,{key:'first'})).json();assert.equal(duplicate.cached,true);assert.equal(duplicate.response.text,'Gaming');
  assert.equal((await reserve(env,{key:'first',fingerprint:'changed'})).status,409);
});
test('session caps hold even after successful low-cost requests',async()=>{
  const env=environment();
  for(let i=0;i<10;i++){assert.equal((await reserve(env,{key:'k'+i})).status,200);await settle(env,'k'+i,{actual:1000});}
  assert.equal((await reserve(env,{key:'eleventh'})).status,429);
});
test('IP cap survives session rotation',async()=>{
  const env=environment();
  for(let i=0;i<30;i++){assert.equal((await reserve(env,{key:'k'+i,session:'s'+i})).status,200);await settle(env,'k'+i,{actual:1000});}
  assert.equal((await reserve(env,{key:'overflow',session:'fresh'})).status,429);
});
test('public gateway requires same-origin session and respects kill switch',async()=>{
  const req=new Request('https://example.org/api/demo',{method:'POST',headers:{Origin:'https://example.org','Content-Type':'application/json'},body:'{"task":"classify","exampleId":"0"}'});
  assert.equal((await worker.fetch(req,environment())).status,401);
  assert.equal((await worker.fetch(req,environment({LIVE_DEMO_ENABLED:'false'}))).status,503);
});
test('unavailable quota storage fails closed before the provider is called',async()=>{
  const env=environment();env.QUOTAS.get=()=>({fetch:async()=>{throw new Error('storage unavailable');}});
  const result=await worker.fetch(new Request('https://example.org/api/llm',{method:'POST',headers:{Authorization:'Bearer research-code','Content-Type':'application/json'},body:'{"task":"name","domain":"posts","words":"charity,gaming"}'}),env);
  assert.equal(result.status,503);assert.match((await result.json()).error,/No model request/);
});
test('a malformed successful reservation fails closed',async()=>{
  const env=environment();env.QUOTAS.get=()=>({fetch:async()=>Response.json({})});
  const result=await worker.fetch(new Request('https://example.org/api/llm',{method:'POST',headers:{Authorization:'Bearer research-code','Content-Type':'application/json'},body:'{"task":"name","domain":"posts","words":"charity,gaming"}'}),env);
  assert.equal(result.status,503);assert.match((await result.json()).error,/No model request/);
});
test('anonymous request sends only server-selected synthetic text to OpenAI',async()=>{
  const previous=globalThis.fetch,env=environment(),cookie=await issueSession(env);let calls=0;
  try{
    globalThis.fetch=async(url,options)=>{calls++;const data=JSON.parse(options.body);assert.match(data.messages[1].content,/Classify/);return Response.json({model:'gpt-4o-2024-08-06',choices:[{finish_reason:'stop',message:{content:'Gaming'}}],usage:{prompt_tokens:100,completion_tokens:1}});};
    const request=()=>new Request('https://example.org/api/demo',{method:'POST',headers:{Origin:'https://example.org',Cookie:'__Host-topicllm='+cookie,'Content-Type':'application/json','X-Request-ID':'repeat-operation'},body:'{"task":"classify","exampleId":"4"}'});
    const first=await worker.fetch(request(),env);assert.equal(first.status,200);assert.equal((await first.json()).mode,'live-synthetic-example');
    const second=await worker.fetch(request(),env),again=await second.json();assert.equal(again.cached,true);assert.equal(again.mode,'live-synthetic-example');assert.equal(calls,1);
  }finally{globalThis.fetch=previous;}
});

test('nonthrowing storage failures cannot report health or release responses',async()=>{
  const previous=globalThis.fetch;
  try{
    globalThis.fetch=async()=>Response.json({model:'gpt-4o-2024-08-06',choices:[{finish_reason:'stop',message:{content:'Gaming'}}],usage:{prompt_tokens:100,completion_tokens:1}});
    for(const failure of [()=>Response.json({error:'storage'}, {status:500}),()=>Response.json({settled:false}),()=>new Response('invalid')]){
      const env=environment(),original=env.QUOTAS.get();
      env.QUOTAS.get=()=>({fetch:request=>new URL(request.url).pathname==='/settle'?failure():original.fetch(request)});
      const result=await worker.fetch(new Request('https://example.org/api/llm',{method:'POST',headers:{Authorization:'Bearer research-code','Content-Type':'application/json'},body:'{"task":"name","domain":"posts","words":"gaming"}'}),env);
      assert.equal(result.status,503);
    }
    const env=environment();env.QUOTAS.get=()=>({fetch:async()=>Response.json({error:'offline'},{status:500})});
    assert.equal((await worker.fetch(new Request('https://example.org/api/health'),env)).status,503);
  }finally{globalThis.fetch=previous;}
});

test('UTC rollover resets public windows but not the one-time validation ceiling',async()=>{
  const original=Date.now;let now=Date.parse('2026-11-30T23:59:00Z');Date.now=()=>now;
  try{
    const env=environment({DEMO_DAILY_USD:'0.001',DEMO_MONTHLY_USD:'0.001',OPERATOR_VALIDATION_USD:'0.001'});
    await reserve(env,{key:'public-nov'});await settle(env,'public-nov');
    await reserve(env,{key:'operator-nov',scope:'operator'});await settle(env,'operator-nov');
    now=Date.parse('2026-12-01T00:01:00Z');
    assert.equal((await reserve(env,{key:'public-dec'})).status,200);
    assert.equal((await reserve(env,{key:'operator-dec',scope:'operator'})).status,429);
  }finally{Date.now=original;}
});

test('stale pending calls retain charges and cannot be settled twice',async()=>{
  const original=Date.now;let now=Date.parse('2026-11-16T12:00:00Z');Date.now=()=>now;
  try{
    const env=environment();await reserve(env,{key:'uncertain'});now+=121000;
    assert.equal((await (await settle(env,'uncertain',{actual:0})).json()).settled,false);
    await reserve(env,{key:'complete'});assert.equal((await(await settle(env,'complete',{actual:1000})).json()).settled,true);
    assert.equal((await(await settle(env,'complete',{actual:0})).json()).settled,false);
    now+=1800001;await env.QUOTAS.get().alarm();
    assert.equal((await(await reserve(env,{key:'complete'})).json()).allowed,true);
  }finally{Date.now=original;}
});
