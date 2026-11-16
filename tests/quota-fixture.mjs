import {DemoQuota} from '../worker/quota.js';
export function quotaBinding(env){
  let queue=Promise.resolve();const values=new Map();
  const tx={get:async key=>structuredClone(values.get(key)),put:async(key,value)=>values.set(key,structuredClone(value))};
  const state={storage:{setAlarm:async()=>{},transaction:fn=>{const result=queue.then(()=>fn(tx));queue=result.catch(()=>{});return result;}}};
  const object=new DemoQuota(state,env);
  return {idFromName:name=>name,get:()=>object};
}
export function environment(overrides={}){
  const env={OPENAI_API_KEY:'test-provider-secret',RESEARCH_ACCESS_TOKEN:'research-code',OPENAI_MODEL:'gpt-4o-2024-08-06',
    LIVE_DEMO_ENABLED:'true',OPERATOR_LLM_ENABLED:'true',DEMO_DAILY_USD:'1',DEMO_MONTHLY_USD:'5',OPERATOR_DAILY_USD:'5',OPERATOR_MONTHLY_USD:'5',
    RATE_LIMITER:{limit:async()=>({success:true})},ASSETS:{fetch:async()=>new Response('asset')},...overrides};
  env.QUOTAS=quotaBinding(env);return env;
}
