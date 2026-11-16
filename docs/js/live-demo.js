import {downloadText} from './util.js';
export async function initLiveDemo(){
  const root=document.getElementById('live-examples');if(!root)return;
  const status=document.getElementById('live-status'),records=[];
  let data;
  try{
    const [examples,config]=await Promise.all([fetch('../data/live-examples.json').then(r=>r.json()),fetch('/api/config').then(r=>r.json())]);data=examples;
    for(const topic of data.topics){const option=new Option(`Topic ${Number(topic.id)+1}`,topic.id);document.getElementById('live-topic').add(option);}
    for(const [i,example] of data.examples.entries())document.getElementById('live-example').add(new Option(`Synthetic post ${i+1}`,example.id));
    status.textContent=config.publicLive?'Live examples are available. Ten calls per browser session per UTC day; shared-network and site-wide limits also apply.':'Live examples are paused. The guided walkthrough and Python downloads remain available.';
    root.querySelectorAll('[data-live-task]').forEach(button=>button.disabled=!config.publicLive);
  }catch{status.textContent='Live access is unavailable. Explore the guided walkthrough or reproduce locally.';return;}
  const update=()=>{
    document.getElementById('live-words').textContent=data.topics.find(t=>t.id===document.getElementById('live-topic').value).words;
    const example=data.examples.find(e=>e.id===document.getElementById('live-example').value);
    document.getElementById('live-text').textContent=example.text;
    document.getElementById('live-truth').textContent=example.generator_theme;
  };
  document.getElementById('live-topic').addEventListener('change',()=>{update();document.getElementById('live-name-result').textContent='Request a name for these topic words.';});
  document.getElementById('live-example').addEventListener('change',()=>{update();document.getElementById('live-classify-result').textContent='Classify this selected synthetic example.';});update();
  for(const button of root.querySelectorAll('[data-live-task]'))button.addEventListener('click',async()=>{
    const task=button.dataset.liveTask,output=document.getElementById(`live-${task}-result`);
    const selection=document.getElementById(task==='name'?'live-topic':'live-example');
    const input=task==='name'?{task,topicId:document.getElementById('live-topic').value}:{task,exampleId:document.getElementById('live-example').value};
    button.disabled=true;selection.disabled=true;output.textContent='Requesting one response from OpenAI…';
    try{
      const session=await fetch('/api/session',{credentials:'same-origin'});if(!session.ok)throw new Error((await session.json()).error);
      const response=await fetch('/api/demo',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-Request-ID':crypto.randomUUID()},body:JSON.stringify(input)});
      const result=await response.json();if(!response.ok)throw new Error(result.error||'The example could not be completed.');
      records.push({input,result,received_at:new Date().toISOString(),mode:'live-synthetic-example'});
      output.replaceChildren();const answer=document.createElement('strong');answer.textContent=result.text;output.append(answer);
      const detail=document.createElement('p');detail.className='note';detail.textContent=`${result.model} · ${result.usage?.total_tokens??'unreported'} tokens · request ${result.request_id??'unreported'}`;output.append(detail);
      status.textContent=`${result.remaining_session??'Limited'} live calls remain in this browser’s daily allowance. These are demonstration responses, not a validated research run.`;
      document.getElementById('live-download').disabled=false;
    }catch(error){output.textContent=error.message;}
    finally{button.disabled=false;selection.disabled=false;}
  });
  document.getElementById('live-download').addEventListener('click',()=>downloadText('topicllm-live-examples.json',JSON.stringify({mode:'live-synthetic-examples',human_validation:false,records},null,2),'application/json'));
}
