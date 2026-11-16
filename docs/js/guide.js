/* Questions send only on submit; conversation stays in page memory. */
const contexts={
 home:['home','A collection of text. A question worth answering.','TopicLLM turns many short texts into themes you can interpret and patterns you can measure. Start with the demonstration; take the reproducible workflow into your own environment when you are ready.','What does TopicLLM do, in plain language?'],
 app:['demo','You are exploring a worked example.','Follow five stages with fictional posts. First see how topics become themes; then calculate how common each theme is across time. The synthetic data make the method tangible.','Walk me through the demo with a simple example.'],
 paper:['methods','This is the recipe behind the demonstration.','Read the five stages in order, or ask the guide to unpack one step. The methods connect each decision to the inputs, outputs and evidence needed to reproduce it.','Explain the five stages without technical jargon.'],
 reproduce:['reproduce','Take the method into your own environment.','Start with a free installation check. Then give your coding agent the research contract and a question. The guide explains the setup; your fork or Python environment runs the analysis.','How do I start with a fork and a coding agent?'],
 validation:['validation','These are measured results on synthetic data.','Inspect what a complete run produced, including its topic count, classifications and cost. This is a software demonstration on generated data, distinct from the dissertation study.','What does this validation establish?'],
 audit:['provenance','Know which evidence you are looking at.','The dissertation is the historical source of truth. The walkthrough explains its method using synthetic data, while the validation record reports a new run on those different data.','Why can the synthetic run find a different number of topics?'],
 privacy:['privacy','Choose what you share, before you send it.','The walkthrough runs locally in your browser. Live examples and guide questions use the hosted OpenAI service. Keep private research records and credentials in your approved environment.','What happens when I send the guide a question?'],
 study1:['study1','Read the original alcohol-marketing study.','This reader displays the unchanged dissertation chapter. It asks how brand messaging changed across the pandemic periods. Use the page controls to explore the source, or ask for a plain-language summary.','What did Study 1 find?'],
 study2:['study2','Read the original longitudinal study.','This chapter examines potential exposure to brand messages and later user-generated posts. The guide can explain the design and interpretation; the reader preserves the original pages.','What did Study 2 find, and what does potential exposure mean?'],
 guide:['guide','A guide to the whole research program.','Ask in your own words. The guide draws on the dissertation and public repository, with source links you can inspect.','Give me an overview of the dissertation.']
};
const route=location.pathname.replace(/^\/TopicLLM/,'').replace(/\/?index\.html$/,'/');
const key=route.startsWith('/studies/1')?'study1':route.startsWith('/studies/2')?'study2':route.split('/').filter(Boolean)[0]||'home',context=contexts[key]||contexts.guide;
const make=(tag,cls,text)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e;};
const orientation=make('aside','page-orientation');orientation.setAttribute('aria-label','Page orientation');
const inner=make('div','orientation-inner'),copy=make('div','orientation-copy');copy.append(make('span','orientation-eyebrow','A place to start'),make('strong','',context[1]),make('p','',context[2]));
const orientButton=make('button','orientation-ask','Ask the guide ↗');orientButton.type='button';inner.append(copy,orientButton);orientation.append(inner);
const main=document.querySelector('main')||document.querySelector('.page');if(key==='home'){const strip=document.querySelector('.release-strip');if(strip)strip.after(orientation);else main?.prepend(orientation);}else main?.prepend(orientation);
const launcher=make('button','guide-launcher');launcher.type='button';launcher.setAttribute('aria-controls','research-guide');launcher.setAttribute('aria-expanded','false');launcher.append(make('span','guide-launch-icon','?'),make('span','','Ask the research guide'));
const invitation=make('aside','guide-invitation');invitation.setAttribute('aria-label','Meet the research guide');
const dismiss=make('button','guide-invitation-dismiss','×');dismiss.type='button';dismiss.setAttribute('aria-label','Dismiss guide introduction');
invitation.append(dismiss,make('span','orientation-eyebrow','Your research companion'),make('strong','','Hi, I’m the TopicLLM guide.'),make('p','','Curious what this does, what the research found, or how to get started? Ask me — we can take it one step at a time.'));
const start=make('button','guide-invitation-start','Start a conversation →');start.type='button';invitation.append(start);try{invitation.hidden=sessionStorage.getItem('topicllm-guide-introduced')==='yes';}catch{}
const dialog=make('dialog','guide-dialog');dialog.id='research-guide';dialog.setAttribute('aria-labelledby','guide-title');
const top=make('div','guide-header'),identity=make('div','guide-identity'),title=make('h2','','TopicLLM guide');title.id='guide-title';identity.append(title,make('p','','AI explanations · sources included'));
const close=make('button','guide-close','×');close.type='button';close.setAttribute('aria-label','Close research guide');top.append(identity,close);
const messages=make('div','guide-messages');messages.setAttribute('role','log');messages.setAttribute('aria-label','Conversation');messages.setAttribute('aria-live','polite');
const greeting=make('div','guide-message guide-answer');greeting.append(make('span','guide-speaker','TopicLLM guide'),make('p','','Hi, I’m your AI guide to TopicLLM. I can explain the software, unpack the dissertation, or help you find your first step. What would you like to understand?'));messages.append(greeting);
const prompts=make('div','guide-prompts'),starters=[context[3],'How are topics different from themes?','How can I reproduce this with an agent?'];
const form=make('form','guide-form'),label=make('label','','Your question');label.htmlFor='guide-question';
const input=make('textarea','');input.id='guide-question';input.rows=2;input.maxLength=1200;input.placeholder='Ask about the method, research, or getting started…';input.required=true;
const disclosure=make('p','guide-disclosure');disclosure.append(document.createTextNode('Sending shares your question and recent chat with OpenAI. No private data or keys. '));const privacy=make('a','','Data handling');privacy.href='/privacy/';privacy.target='_blank';privacy.rel='noopener';disclosure.append(privacy);
const controls=make('div','guide-controls'),clear=make('button','guide-clear','Clear conversation'),send=make('button','guide-send','Send question →');clear.type='button';send.type='submit';controls.append(clear,send);
const status=make('p','guide-status','AI can make mistakes. Check the linked sources.');status.setAttribute('role','status');const fallback=make('p','guide-fallback');for(const [name,url] of [['Read the briefing','/guide/knowledge.md'],['Explore the demo','/app/']]){const a=make('a','',name);a.href=url;a.target='_blank';a.rel='noopener';fallback.append(a);}form.append(label,input,disclosure,controls,status,fallback);messages.append(prompts);dialog.append(top,messages,form);document.body.append(invitation,launcher,dialog);
let history=[],busy=false,op=null,lastFocused;
function introduced(){invitation.hidden=true;try{sessionStorage.setItem('topicllm-guide-introduced','yes');}catch{}}
function openGuide(question){introduced();lastFocused=document.activeElement;if(!dialog.open)dialog.showModal();launcher.setAttribute('aria-expanded','true');if(question)input.value=question;input.focus();}
function closeGuide(){dialog.close();launcher.setAttribute('aria-expanded','false');lastFocused?.focus();}
function suggestions(items){prompts.replaceChildren();for(const question of items){const b=make('button','',question);b.type='button';b.disabled=busy;b.addEventListener('click',()=>{input.value=question;input.focus();});prompts.append(b);}}
suggestions(starters);launcher.addEventListener('click',()=>openGuide());start.addEventListener('click',()=>openGuide());orientButton.addEventListener('click',()=>openGuide(context[3]));dismiss.addEventListener('click',introduced);close.addEventListener('click',closeGuide);dialog.addEventListener('close',()=>launcher.setAttribute('aria-expanded','false'));
document.addEventListener('click',e=>{const b=e.target.closest('[data-ask-guide]');if(b)openGuide(b.dataset.askGuide||'');});
clear.addEventListener('click',()=>{if(busy)return;history=[];op=null;messages.replaceChildren(greeting,prompts);input.value='';status.textContent='Conversation cleared from this page. Short server receipts expire within 30 minutes.';suggestions(starters);input.focus();});
input.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();form.requestSubmit();}});
async function request(path,options={}){const r=await fetch(path,{credentials:'same-origin',cache:'no-store',...options});let body;try{body=await r.json();}catch{throw new Error('The guide could not connect.');}if(!r.ok)throw new Error(body.error||'The guide is unavailable.');return body;}
form.addEventListener('submit',async e=>{
 e.preventDefault();if(busy||!input.value.trim())return;const question=input.value.trim(),recent=[];let size=0;
 for(let i=history.length-2;i>=0&&recent.length<6;i-=2){const pair=history.slice(i,i+2),chars=pair.reduce((n,m)=>n+m.content.length,0);if(size+chars>8500)break;recent.unshift(...pair);size+=chars;}
 const serialized=JSON.stringify({question,history:recent,page:context[0]});if(!op||op.payload!==serialized)op={id:crypto.randomUUID(),payload:serialized};
 busy=true;send.disabled=clear.disabled=input.disabled=true;prompts.querySelectorAll('button').forEach(b=>b.disabled=true);status.textContent='Reading the research notes and preparing a clear answer…';
 const asked=make('div','guide-message guide-question');asked.append(make('span','guide-speaker','You'),make('p','',question));messages.insertBefore(asked,prompts);messages.scrollTop=messages.scrollHeight;
 let receivedAnswer=null;
 try{
  const config=await request('/api/config');if(!config.guideLive)throw new Error('The live guide is unavailable right now.');await request('/api/session');
  const result=await request('/api/guide',{method:'POST',headers:{'Content-Type':'application/json','X-Request-ID':op.id},body:serialized,signal:AbortSignal.timeout(60000)});
  const answer=make('div','guide-message guide-answer');receivedAnswer=answer;answer.append(make('span','guide-speaker','TopicLLM guide'));for(const p of result.text.split(/\n\s*\n/))answer.append(make('p','',p));
  const links=make('div','guide-sources');links.setAttribute('aria-label','Sources for this answer');for(const source of result.sources||[]){const a=make('a','',source.title);a.href=source.url;a.target='_blank';a.rel='noopener';links.append(a);}answer.append(links);messages.insertBefore(answer,prompts);history.push({role:'user',content:question},{role:'assistant',content:result.text});input.value='';op=null;
  status.textContent=`${result.remaining_session} shared live calls remain today. AI can make mistakes; check the sources.`;busy=false;suggestions(result.suggestions?.length?result.suggestions:starters);
 }catch(error){asked.remove();status.textContent=(error.name==='TimeoutError'?'The request took too long. Retry the same question to recover a completed response safely.':error.message)+' The visual demo and research briefing remain available.';}
 finally{busy=false;send.disabled=clear.disabled=input.disabled=false;prompts.querySelectorAll('button').forEach(b=>b.disabled=false);input.focus({preventScroll:true});if(receivedAnswer)messages.scrollTop+=receivedAnswer.getBoundingClientRect().top-messages.getBoundingClientRect().top-18;}
});
