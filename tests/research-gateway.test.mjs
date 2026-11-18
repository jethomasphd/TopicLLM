import test from 'node:test';
import assert from 'node:assert/strict';
import {validateOperatorCall} from '../worker/provider.js';
import {demoCall} from '../worker/index.js';
import {environment} from './quota-fixture.mjs';
const reserve=(env,input)=>env.QUOTAS.get('x').fetch(new Request('https://quota/reserve',{method:'POST',body:JSON.stringify({scope:'operator',session:'operator',ip:'test',fingerprint:'test',...input})}));
const settle=(env,key,extra)=>env.QUOTAS.get('x').fetch(new Request('https://quota/settle',{method:'POST',body:JSON.stringify({key,ok:true,http_status:200,response:{text:'test'},...extra})}));

test('operator preserves a frozen codebook prompt while public examples reject it',()=>{
  const input={task:'classify',_research_prompt:{system:'You are an expert at classifying text into themes.',user:'A frozen coding guide and source document.',temperature:.5,max_tokens:120}};
  assert.equal(validateOperatorCall(input).user,input._research_prompt.user);
  assert.throws(()=>demoCall(input));
  assert.throws(()=>validateOperatorCall({...input,_research_prompt:{...input._research_prompt,max_tokens:10000}}));
  assert.throws(()=>validateOperatorCall({...input,_research_prompt:{...input._research_prompt,temperature:1}}));
});

test('an authorized research run has a finite lifetime allowance separate from prior validation',async()=>{
  const env=environment({OPERATOR_RUN_ID:'campaign-presidency-test',OPERATOR_VALIDATION_USD:'0.001'});
  assert.equal((await reserve(env,{scope:'operator',key:'research-budget-one',reserved:1000000})).status,200);
  await settle(env,'research-budget-one',{actual:1000000});
  assert.equal((await reserve(env,{scope:'operator',key:'research-budget-two',reserved:1})).status,429);
});

test('research naming accepts a declared 32-token ceiling with a finite upper bound',()=>{
  const input={task:'name',_research_prompt:{system:'You are an expert at naming topics.',user:'Name this topic.',temperature:.5,max_tokens:32}};
  assert.equal(validateOperatorCall(input).max_tokens,32);
  assert.throws(()=>validateOperatorCall({...input,_research_prompt:{...input._research_prompt,max_tokens:65}}));
});
