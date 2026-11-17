import {downloadText} from './util.js';
export async function initLiveDemo(){
 const root=document.getElementById('live-examples');if(!root)return;
 const $=id=>document.getElementById(id),status=$('live-status'),records=[];
 let data,available=false,busy=false,filtered=[];
 try{
  const [a,b]=await Promise.all([fetch('../data/live-examples.json'),fetch('/api/config')]);
  if(!a.ok||!b.ok)throw new Error();data=await a.json();const config=await b.json();available=config.publicLive;
  for(const topic of data.topics)$('live-topic').add(new Option(`Recorded topic ${Number(topic.id)+1} · ${topic.count} posts`,topic.id));
  status.textContent=available?`Explore original Study 1 data with OpenAI. ${config.sessionCallsPerDay} calls per browser session and ${config.ipCallsPerDay} per shared network each UTC day; $${config.dailyUsd} site-wide daily allowance.`:'Live examples are paused. The original-data walkthrough and downloads remain available.';
 }catch{status.textContent='Live access is unavailable. Explore the original-data walkthrough or run locally.';return;}
 const controls=()=>root.querySelectorAll('button,select,input').forEach(el=>{el.disabled=busy||(!available&&el.matches('[data-live-task]'));});
 const update=()=>{
  $('live-words').textContent=data.topics.find(t=>t.id===$('live-topic').value)?.words||'';
  const e=data.examples.find(e=>e.id===$('live-example').value);
  $('live-text').textContent=e?.text||'No posts match. Try another word or brand.';
  $('live-truth').textContent=e?`${e.brand} · ${e.date} · ${e.post_id}. Original brand post; no human theme label is asserted.`:'';
 };
 function filter(){const q=$('live-search').value.toLowerCase().trim();filtered=data.examples.filter(e=>!q||`${e.brand} ${e.date} ${e.post_id} ${e.text}`.toLowerCase().includes(q));$('live-example').replaceChildren(...filtered.slice(0,100).map(e=>new Option(`${e.brand} · ${e.date} · ${e.post_id}`,e.id)));$('live-match-count').textContent=`${filtered.length.toLocaleString()} matching posts${filtered.length>100?' · showing the first 100; narrow your search or pick a random match':''}`;update();}
 $('live-search').addEventListener('input',filter);$('live-topic').addEventListener('change',update);$('live-example').addEventListener('change',update);
 $('live-random').onclick=()=>{if(!filtered.length)return;const e=filtered[Math.floor(Math.random()*filtered.length)];if(![...$('live-example').options].some(o=>o.value===e.id))$('live-example').add(new Option(`${e.brand} · ${e.date} · ${e.post_id}`,e.id));$('live-example').value=e.id;update();};filter();controls();
 for(const button of root.querySelectorAll('[data-live-task]'))button.addEventListener('click',async()=>{
  if(busy)return;const task=button.dataset.liveTask;if(task==='classify'&&!$('live-example').value)return;
  const input=task==='name'?{task,topicId:$('live-topic').value}:{task,exampleId:$('live-example').value};
  const n=task==='name'?Number($('live-votes').value):1,output=$(`live-${task}-result`),ballots=[];
  busy=true;controls();
  try{
   const session=await fetch('/api/session',{credentials:'same-origin'});if(!session.ok)throw new Error((await session.json()).error);
   for(let i=0;i<n;i++){
    output.textContent=`Requesting independent response ${i+1} of ${n}…`;
    const response=await fetch('/api/demo',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-Request-ID':crypto.randomUUID()},body:JSON.stringify(input),signal:AbortSignal.timeout(60000)});
    const result=await response.json();if(!response.ok)throw new Error(result.error||'The request could not be completed.');
    records.push({input,result,received_at:new Date().toISOString(),mode:'live-study1-example'});ballots.push(result.text);
    status.textContent=`${result.remaining_session} shared live calls remain today. Original data; illustrative responses for you to inspect.`;
   }
   output.replaceChildren();const tally=new Map();for(const label of ballots)tally.set(label,(tally.get(label)||0)+1);
   for(const [label,count] of [...tally].sort((a,b)=>b[1]-a[1])){const p=document.createElement('p'),b=document.createElement('strong');b.textContent=label;p.append(b,document.createTextNode(n>1?` — ${count}/${n} votes`:''));output.append(p);}
   const detail=document.createElement('p');detail.className='note';detail.textContent=task==='name'?`${n} independent calls, with the full tally retained. More votes reveal variation; they do not replace researcher interpretation.`:'One live classification, not an independently validated research label.';output.append(detail);
  }catch(error){output.textContent=`${error.message}${ballots.length?` ${ballots.length} completed responses are retained in your download.`:''}`;}
  finally{busy=false;controls();$('live-download').disabled=!records.length;}
 });
 $('live-download').onclick=()=>downloadText('topicllm-study1-live-responses.json',JSON.stringify({mode:'original-study1-illustration',human_validation:false,records},null,2),'application/json');
}
