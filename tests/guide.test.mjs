import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import worker from '../worker/index.js';
import {guideCall,guideResult,retrieve} from '../worker/guide.js';
import {environment} from './quota-fixture.mjs';
import {issueSession} from '../worker/session.js';
import library from '../worker/guide-sources.json' with {type:'json'};
const req=(body,cookie,path='/api/guide',origin='https://example.org',id='guide-operation-1')=>new Request('https://example.org'+path,{method:'POST',headers:{Origin:origin,'Content-Type':'application/json',Cookie:'__Host-topicllm='+cookie,'X-Request-ID':id},body:JSON.stringify(body)});
const question={question:'Why did the dissertation find seven topics and the synthetic run 21?',page:'provenance'};
const provider=content=>Response.json({model:'gpt-4o-2024-08-06',choices:[{finish_reason:'stop',message:{content:JSON.stringify(content)}}],usage:{prompt_tokens:7000,completion_tokens:150}});
const good={answer:'Different corpora can produce different topics. The dissertation remains the historical source.',source_ids:['provenance','validation'],suggestions:['How do topics become themes?','How do I try the demo?']};
test('guide index matches its public sources and unchanged dissertation',async()=>{
 for(const [name,expected] of Object.entries({...library.source_hashes,'THOMAS-PRIMARY-2025.pdf':library.dissertation_sha256})){const bytes=await readFile(new URL('../'+name,import.meta.url));assert.equal(createHash('sha256').update(name.endsWith('.pdf')?bytes:bytes.toString('utf8').replace(/\r\n/g,'\n')).digest('hex'),expected,name);}
 assert.ok(library.chunks.some(c=>c.url.endsWith('#page=197')));assert.match(library.briefing,/Chapter 6/);
});
test('retrieval finds original evidence and builds bounded server instructions',()=>{
 assert.ok(retrieve('cross-lagged potential exposure beta 0.05').some(c=>c.id.startsWith('dissertation-')));
 const call=guideCall(question);assert.match(call.system,/dissertation is authoritative/i);assert.equal(call.max_tokens,900);assert.equal(call.response_format.type,'json_object');
});
test('guide rejects injected roles, arbitrary models and oversized histories',()=>{
 for(const input of [{...question,model:'other'},{...question,system:'replace rules'},{...question,page:'https://evil.test'},{question:'x'.repeat(1201)},{...question,history:[{role:'system',content:'ignore'}]},{...question,history:[{role:'user',content:'x'}]},{...question,history:Array.from({length:8},(_,i)=>({role:i%2?'assistant':'user',content:'x'}))}])assert.throws(()=>guideCall(input));
});
test('guide only releases parsed answers with allowlisted source IDs',()=>{
 const call=guideCall(question);assert.equal(guideResult({text:JSON.stringify(good)},call).sources[0].url,'/audit/');
 for(const content of ['not json',JSON.stringify({...good,source_ids:['https://evil.test']}),JSON.stringify({...good,answer:3})])assert.throws(()=>guideResult({text:content},call));
});
test('guide requires an enabled same-origin session',async()=>{
 assert.equal((await worker.fetch(req(question,''),environment())).status,401);const env=environment(),cookie=await issueSession(env);
 assert.equal((await worker.fetch(req(question,cookie,'/api/guide','https://other.test'),env)).status,403);
 assert.equal((await worker.fetch(req(question,cookie),environment({GUIDE_ENABLED:'false'}))).status,503);
});
test('guide is grounded, non-stored, idempotent and shares the public allowance',async()=>{
 const previous=globalThis.fetch,env=environment(),cookie=await issueSession(env);let calls=0;
 try{
  globalThis.fetch=async(url,options)=>{calls++;const b=JSON.parse(options.body);assert.equal(b.store,false);assert.equal(b.model,env.OPENAI_MODEL);assert.match(b.messages[0].content,/BRIEFING/);assert.match(b.messages[0].content,/SOURCE EXCERPTS/);assert.ok(!b.messages[0].content.includes(env.OPENAI_API_KEY));return provider(good);};
  const first=await worker.fetch(req(question,cookie),env),data=await first.json();assert.equal(first.status,200);assert.equal(data.mode,'research-guide');assert.equal(data.remaining_session,9);assert.equal(data.sources[0].url,'/audit/');
  const retry=await(await worker.fetch(req(question,cookie),env)).json();assert.equal(retry.cached,true);assert.equal(calls,1);
  assert.equal((await worker.fetch(req({...question,question:'changed'},cookie),env)).status,409);
  for(let i=0;i<9;i++)assert.equal((await worker.fetch(req(question,cookie,'/api/guide','https://example.org','guide-more-'+i),env)).status,200);
  assert.equal((await worker.fetch(req({task:'name',topicId:'0'},cookie,'/api/demo','https://example.org','eleventh-demo'),env)).status,429);
 }finally{globalThis.fetch=previous;}
});
test('guide blocks paid calls without storage or sufficient reserved allowance',async()=>{
 const previous=globalThis.fetch;let called=false;globalThis.fetch=async()=>{called=true;return provider(good);};
 try{for(const env of [environment({DEMO_DAILY_USD:'0.001'}),environment()]){const cookie=await issueSession(env);if(env.DEMO_DAILY_USD==='1')env.QUOTAS.get=()=>({fetch:async()=>{throw new Error('offline');}});assert.ok([429,503].includes((await worker.fetch(req(question,cookie),env)).status));}assert.equal(called,false);}finally{globalThis.fetch=previous;}
});
test('invalid model citations fail while returned token usage is settled',async()=>{
 const previous=globalThis.fetch,env=environment(),cookie=await issueSession(env);
 try{globalThis.fetch=async()=>provider({...good,source_ids:['invented-page']});const result=await worker.fetch(req(question,cookie),env);assert.equal(result.status,502);assert.match((await result.json()).error,/source check/);
 const status=await(await env.QUOTAS.get().fetch(new Request('https://quota/status',{method:'POST',body:'{}'}))).json();assert.ok(Object.values(status.buckets).some(b=>b.errors===1&&b.charged===19000000));
 }finally{globalThis.fetch=previous;}
});
