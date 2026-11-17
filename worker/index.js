import examples from '../docs/data/live-examples.json' with {type:'json'};
import {validateCall,sendOpenAI} from './provider.js';
import {hash,sign,equal,session,issueSession} from './session.js';
import {guideCall,guideResult,GUIDE_VERSION} from './guide.js';
import {publicLimits} from './limits.js';
export {validateCall};
export {DemoQuota} from './quota.js';
const json=(data,status=200,headers={})=>Response.json(data,{status,headers:{'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',...headers}});
const configured=env=>!!(env.OPENAI_API_KEY&&env.RESEARCH_ACCESS_TOKEN&&env.OPENAI_MODEL==='gpt-4o-2024-08-06'&&env.RATE_LIMITER&&env.QUOTAS);
const operator=async(request,env)=>equal(request.headers.get('Authorization')||'',`Bearer ${env.RESEARCH_ACCESS_TOKEN}`);
const quota=(env,path,data)=>env.QUOTAS.get(env.QUOTAS.idFromName('topicllm-global-v1')).fetch(new Request('https://quota'+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}));

async function readBody(request){
  if(!request.headers.get('Content-Type')?.toLowerCase().startsWith('application/json'))throw Object.assign(new Error('Use application/json.'),{status:415});
  const reader=request.body?.getReader();if(!reader)throw new Error('Request body is required.');
  let size=0;const parts=[];
  while(true){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>24000){await reader.cancel();throw Object.assign(new Error('Request too large.'),{status:413});}parts.push(value);}
  const body=new Uint8Array(size);let offset=0;for(const part of parts){body.set(part,offset);offset+=part.length;}
  return JSON.parse(new TextDecoder().decode(body));
}

export function demoCall(input){
  if(!input||!['name','classify'].includes(input.task))throw new Error('Select a Study 1 example.');
  const field=input.task==='name'?'topicId':'exampleId';
  if(Object.keys(input).some(k=>!['task',field].includes(k)))throw new Error('The public demo accepts released Study 1 example IDs only.');
  if(input.task==='name'){
    const topic=examples.topics.find(t=>t.id===input.topicId);if(!topic)throw new Error('Unknown recorded topic.');
    return {task:'name',words:topic.words,domain:examples.domain};
  }
  const example=examples.examples.find(e=>e.id===input.exampleId);if(!example)throw new Error('Unknown Study 1 example.');
  return {task:'classify',text:example.text,themes:examples.themes};
}

export default {async fetch(request,env){
  const url=new URL(request.url),path=url.pathname;
  // Keep existing API clients on their origin; browser navigation uses the primary domain.
  if(env.CANONICAL_REDIRECTS!=='false'&&!path.startsWith('/api/')&&['GET','HEAD'].includes(request.method)&&
     ['topicllm.dev','www.topicllm.dev','topicllm.jethomasphd.workers.dev'].includes(url.hostname)&&
     (url.hostname!=='topicllm.dev'||url.protocol!=='https:')){
    url.hostname='topicllm.dev';url.protocol='https:';url.port='';
    return Response.redirect(url.href,308);
  }
  if(!path.startsWith('/api/'))return env.ASSETS.fetch(request);
  const ready=configured(env), publicLive=ready&&env.LIVE_DEMO_ENABLED==='true';
  const guideLive=publicLive&&env.GUIDE_ENABLED==='true';
  if(path==='/api/config'&&request.method==='GET')return json({ready,provider:'openai',model:env.OPENAI_MODEL||null,access:'released-study1-examples-and-research-guide',publicLive,guideLive,guideVersion:GUIDE_VERSION,maxTextLength:8000,...publicLimits(env)});
  if(path==='/api/health'&&request.method==='GET'){
    try{
      if(!ready)return json({status:'unconfigured',live_examples:false},503);
      if(!(await env.RATE_LIMITER.limit({key:'health:'+(request.headers.get('CF-Connecting-IP')||'unknown')})).success)return json({status:'rate-limited'},429,{'Retry-After':'60'});
      const response=await quota(env,'/status',{}),status=await response.json();
      if(!response.ok||!status.utc_day||!status.buckets)throw new Error('Quota health unavailable');
      return json({status:'ok',live_examples:publicLive,model:env.OPENAI_MODEL});
    }catch{return json({status:'unavailable',live_examples:false},503);}
  }
  if(!['/api/session','/api/demo','/api/guide','/api/llm','/api/admin/status'].includes(path))return json({error:'Not found.'},404);
  if(!ready)return json({error:'Live access is unavailable. The visual walkthrough remains available.'},503);
  const origin=request.headers.get('Origin');
  if(origin&&origin!==url.origin)return json({error:'Cross-origin calls are not allowed.'},403);
  if(path==='/api/admin/status'){
    if(!await operator(request,env))return json({error:'Operator authorization required.'},401);
    const result=await quota(env,'/status',{});return json(await result.json(),result.status);
  }
  if(path==='/api/session'){
    if(request.method!=='GET')return json({error:'Use GET.'},405,{Allow:'GET'});
    if(!publicLive)return json({error:'Live examples are temporarily paused.'},503);
    const ip=request.headers.get('CF-Connecting-IP');if(!ip)return json({error:'Client address unavailable.'},503);
    if(!(await env.RATE_LIMITER.limit({key:'session:'+ip})).success)return json({error:'Please wait before starting another demo session.'},429,{'Retry-After':'60'});
    if(await session(request,env))return json({ready:true});
    return json({ready:true},200,{'Set-Cookie':`__Host-topicllm=${await issueSession(env)}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=86400`});
  }
  if(request.method!=='POST')return json({error:'Use POST.'},405,{Allow:'POST'});
  const isGuide=path==='/api/guide',isPublic=path==='/api/demo'||isGuide;
  let identity;
  if(isPublic){
    if(isGuide&&!guideLive)return json({error:'The live guide is temporarily unavailable. Explore the walkthrough or read the research briefing.',retryable:false},503);
    if(!publicLive)return json({error:'Live examples are temporarily paused.'},503);
    if(origin!==url.origin)return json({error:'Open the live demo on this website.'},403);
    identity=await session(request,env);if(!identity)return json({error:'Start a new demo session.',retryable:false},401);
  }else{
    if(env.OPERATOR_LLM_ENABLED!=='true')return json({error:'Operator calls are paused.'},503);
    if(!await operator(request,env))return json({error:'Operator authorization required. Use the public visual demo or your own Python environment.'},401);
    identity='operator';
  }
  const ip=request.headers.get('CF-Connecting-IP')||'local-operator';
  const limiter=isPublic?env.RATE_LIMITER:(env.OPERATOR_RATE_LIMITER||env.RATE_LIMITER);
  if(!(await limiter.limit({key:(isPublic?'demo:':'operator:')+ip})).success)return json({error:'Request rate exceeded. Wait one minute and retry.',retryable:true},429,{'Retry-After':'60'});
  let call,input;
  try{input=await readBody(request);call=isGuide?guideCall(input):validateCall(isPublic?demoCall(input):input);}catch(error){return json({error:error instanceof SyntaxError?'Malformed JSON.':error.message,retryable:false},error.status||400);}
  const operation=request.headers.get('X-Request-ID')||crypto.randomUUID();
  if(!/^[a-zA-Z0-9_-]{8,100}$/.test(operation))return json({error:'Invalid operation ID.'},400);
  const key=`${identity}:${isGuide?'guide:':''}${operation}`, fingerprint=isGuide?await sign(JSON.stringify(call),env.RESEARCH_ACCESS_TOKEN):await hash(JSON.stringify(call));
  const ipHash=await sign(`ip:${new Date().toISOString().slice(0,10)}:${ip}`,env.RESEARCH_ACCESS_TOKEN);
  const reserved=(new TextEncoder().encode(call.system+call.user).length+256)*2500+call.max_tokens*10000;
  let reservation;
  try{
    const response=await quota(env,'/reserve',{scope:isPublic?'public':'operator',key,session:identity,ip:ipHash,fingerprint,reserved});
    reservation=await response.json();
    if(!response.ok)return json(reservation,response.status,reservation.retry_after?{'Retry-After':String(reservation.retry_after)}:{});
    if(reservation.cached)return json({...reservation.response,cached:true},reservation.http_status);
    if(reservation.allowed!==true)throw new Error('Reservation was not confirmed');
  }catch{return json({error:'Usage controls are unavailable. No model request was sent.',retryable:false},503);}
  const response=await sendOpenAI(call,env);let providerResult=await response.json(),httpStatus=response.status,ok=response.ok;
  if(isGuide&&ok){try{providerResult=guideResult(providerResult,call);}catch(error){providerResult={error:error.message,usage:providerResult.usage,retryable:false};httpStatus=502;ok=false;}}
  const result={...providerResult,...(isPublic?{mode:isGuide?'research-guide':'live-study1-example',remaining_session:reservation.remaining_session}:{})};
  const usage=result.usage;
  const actual=Number.isInteger(usage?.prompt_tokens)&&Number.isInteger(usage?.completion_tokens)?usage.prompt_tokens*2500+usage.completion_tokens*10000:null;
  try{
    const settled=await quota(env,'/settle',{key,actual,ok,response:result,http_status:httpStatus});
    if(!settled.ok||(await settled.json()).settled!==true)throw new Error('Settlement failed');
  }
  catch{return json({error:'The response could not be recorded safely. No label was released; the allowance remains reserved.',retryable:false},503);}
  const headers={};if(response.headers.has('Retry-After'))headers['Retry-After']=response.headers.get('Retry-After');
  return json(result,httpStatus,headers);
}};
