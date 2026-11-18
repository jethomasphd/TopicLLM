import {downloadText} from './util.js';
export async function initLiveDemo(){
 const root=document.getElementById('live-examples');if(!root)return;
 const $=id=>document.getElementById(id),status=$('live-status'),records=[];
 let data,available=false,busy=false,filtered=[],viewedTopic=null,viewedExample=null;
 try{
  const [a,b]=await Promise.all([fetch('../data/trump/live-examples.json'),fetch('/api/config')]);
  if(!a.ok||!b.ok)throw new Error();data=await a.json();const config=await b.json();available=config.publicLive;
  for(const topic of data.topics)$('live-topic').add(new Option(`Recorded topic ${topic.id} · ${topic.count} posts`,topic.id));
  status.textContent=available?`Live OpenAI is ready. Up to ${config.sessionCallsPerDay} shared calls per browser session today; service limits apply.`:'Live examples are paused. The recorded walkthrough and downloads remain available.';
 }catch{status.textContent='Live access is unavailable. Explore the recorded walkthrough or run locally.';return;}
 for(const theme of data.themes){const li=document.createElement('li');const heading=document.createElement('strong');heading.textContent=theme;li.append(heading);if(data.codebook?.themes[theme]){const details=document.createElement('details'),summary=document.createElement('summary'),definition=document.createElement('p');summary.textContent='Definition and boundaries';definition.textContent=data.codebook.themes[theme];definition.style.whiteSpace='pre-wrap';details.append(summary,definition);li.append(details);}$('live-categories')?.append(li);}
 const controls=()=>root.querySelectorAll('button,select,input').forEach(el=>{el.disabled=busy||(!available&&el.matches('[data-live-task]'))||(el.matches('[data-live-task="classify"]')&&!$('live-example').value)||(el.id==='live-download'&&!records.length)||(['live-random','live-example'].includes(el.id)&&!filtered.length);});
 const update=()=>{
  $('live-words').textContent=data.topics.find(t=>t.id===$('live-topic').value)?.words||'';
  const e=data.examples.find(e=>e.id===$('live-example').value);
  if(viewedTopic!==$('live-topic').value)$('live-name-result').textContent='The complete tally and model details will be available to download.';
  if(viewedExample!==(e?.id||null))$('live-classify-result').textContent='A single model choice is an example to inspect, not an independently validated label.';
  viewedTopic=$('live-topic').value;viewedExample=e?.id||null;
  $('live-text').textContent=e?.text||'No posts match. Try another word or date.';
  $('live-truth').textContent=e?`${e.date} · ${e.post_id} · ${e.is_retweet==='t'?'Retweet':'Account post'}. Public archive; practice classification only.`:'';
 };
 function filter(){const terms=$('live-search').value.toLowerCase().trim().split(/\s+/).filter(Boolean);filtered=data.examples.filter(e=>{const text=`${e.date} ${e.post_id} ${e.text}`.toLowerCase();return terms.every(term=>text.includes(term));});$('live-example').replaceChildren(...filtered.slice(0,100).map(e=>new Option(`${e.date} · ${e.post_id}`,e.id)));$('live-match-count').textContent=`${filtered.length.toLocaleString()} matching ${filtered.length===1?'post':'posts'}${filtered.length>100?' · showing the first 100; narrow your search or pick a random match':''}`;update();controls();}
 $('live-search').addEventListener('input',filter);$('live-topic').addEventListener('change',update);$('live-example').addEventListener('change',update);
 $('live-random').onclick=()=>{if(!filtered.length)return;const e=filtered[Math.floor(Math.random()*filtered.length)];if(![...$('live-example').options].some(o=>o.value===e.id))$('live-example').add(new Option(`${e.date} · ${e.post_id}`,e.id));$('live-example').value=e.id;update();};filter();controls();
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
    const result=await response.json();
    const source=task==='name'?{topic:data.topics.find(t=>t.id===input.topicId),domain:data.domain}:{example:data.examples.find(e=>e.id===input.exampleId),categories:[...data.themes,'The text does not fit into any of these themes'],codebook:data.codebook,codebook_sha256:data.codebook_sha256};
    records.push({input,source,result,http_status:response.status,received_at:new Date().toISOString(),mode:'live-trump-example'});
    if(Number.isInteger(result.remaining_session))status.textContent=`${result.remaining_session} shared live calls remain today. Public archive; illustrative responses for you to inspect.`;
    if(!response.ok)throw new Error(result.error||'The request could not be completed.');ballots.push(result.text);
   }
   output.replaceChildren();const tally=new Map();for(const label of ballots)tally.set(label,(tally.get(label)||0)+1);
   for(const [label,count] of [...tally].sort((a,b)=>b[1]-a[1])){const p=document.createElement('p'),b=document.createElement('strong');b.textContent=label;p.append(b,document.createTextNode(n>1?` — ${count}/${n} votes`:''));output.append(p);}
   const detail=document.createElement('p');detail.className='note';detail.textContent=task==='name'?`${n} independent ${n===1?'call':'calls'}, with the full tally retained. More votes reveal variation; they do not replace researcher interpretation.`:'One live classification, not an independently validated research label.';output.append(detail);
  }catch(error){output.textContent=`${error.message}${ballots.length?` ${ballots.length} completed responses are retained in your download.`:''}`;}
  finally{busy=false;controls();$('live-download').disabled=!records.length;}
 });
 $('live-download').onclick=()=>downloadText('topicllm-trump-live-responses.json',JSON.stringify({schema_version:1,mode:'public-trump-tutorial',dataset:data.dataset,corpus_sha256:data.corpus_sha256,taxonomy_status:data.taxonomy_status,human_synthesis:data.human_review_performed,classifier_validated:false,codebook_sha256:data.codebook_sha256,records},null,2),'application/json');
}
