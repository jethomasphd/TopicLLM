/* TopicLLM guide: one Ask panel, opened only from a [data-ask] control or the
 * #ask address. It never opens itself. Questions are sent only on submit and the
 * conversation lives in page memory only: nothing is stored in the browser. */
const API='/api/guide';
const STARTERS=['What did the tutorial find?','Why did the classifier fail?','Can I use this on my own data?','What do the humans have to do?'];
const GREETING='I’m the TopicLLM guide, an AI. I can explain the method, the tutorial’s numbers, or how to run this on your own data. What are you trying to do?';
const FOOTER='AI-generated explanations of public materials. Not a reviewer.';
const MAX_FOLLOW_UPS=3;

// Page context sent with each question; retired pages map to the names older servers know.
function pageContext(){
  const parts=location.pathname.replace(/^\/TopicLLM(?=\/)/,'').split('/').filter(p=>p&&p!=='index.html');
  if(parts[0]==='studies')return parts[1]==='1'?'study1':parts[1]==='2'?'study2':'home';
  return {tutorial:'tutorial',use:'use',research:'research',paper:'methods',privacy:'privacy',app:'demo',data:'data',validation:'validation',reproduce:'reproduce',audit:'provenance',welcome:'welcome',guide:'guide'}[parts[0]]||'home';
}

function el(tag,attrs={},...children){
  const node=document.createElement(tag);
  for(const [key,value] of Object.entries(attrs))if(value!==false&&value!=null)node.setAttribute(key,value===true?'':value);
  node.append(...children);
  return node;
}
const hidden=text=>el('span',{class:'ask-sr'},text);
const closeIcon=()=>{
  const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg'),path=document.createElementNS(ns,'path');
  for(const [k,v] of Object.entries({viewBox:'0 0 24 24',width:'20',height:'20','aria-hidden':'true',focusable:'false'}))svg.setAttribute(k,v);
  for(const [k,v] of Object.entries({d:'M6 6l12 12M18 6L6 18',fill:'none',stroke:'currentColor','stroke-width':'2','stroke-linecap':'round'}))path.setAttribute(k,v);
  svg.append(path);return svg;
};
// Only same-origin pages and HTTPS sources become links; anything else renders as text.
function safeHref(url){
  try{const u=new URL(String(url),location.origin);if(u.origin===location.origin)return u.pathname+u.search+u.hash;if(u.protocol==='https:')return u.href;}catch{}
  return null;
}
// randomUUID needs a secure context; getRandomValues covers plain-HTTP previews.
const operationId=()=>crypto.randomUUID?.()||[...crypto.getRandomValues(new Uint8Array(16))].map(b=>b.toString(16).padStart(2,'0')).join('');
const reducedMotion=()=>matchMedia('(prefers-reduced-motion: reduce)').matches;

function mount(){
  if(globalThis.__topicllmAsk)return;
  globalThis.__topicllmAsk=true;
  if(!document.querySelector('link[href$="guide.css"]'))document.head.append(el('link',{rel:'stylesheet',href:new URL('../guide.css',import.meta.url).href}));

  const page=pageContext();
  const title=el('h2',{class:'ask-title',id:'ask-title',tabindex:'-1'},'TopicLLM guide');
  const close=el('button',{type:'button',class:'ask-close','aria-label':'Close guide'},closeIcon());
  const greeting=el('div',{class:'ask-msg ask-msg--guide'},el('p',{id:'ask-greeting'},GREETING));
  const log=el('div',{class:'ask-log',role:'log','aria-live':'polite','aria-label':'Conversation'},greeting);
  const chips=el('div',{class:'ask-chips',role:'group','aria-label':'Suggested questions'});
  const scroll=el('div',{class:'ask-scroll'},log,chips);
  const input=el('textarea',{id:'ask-input',class:'ask-input',rows:'1',maxlength:'1200',required:true,placeholder:'Ask a question…',autocomplete:'off'});
  const send=el('button',{type:'submit',class:'ask-send'},'Send');
  const privacy=el('a',{href:'/privacy/',target:'_blank',rel:'noopener'},'How questions are handled');
  const form=el('form',{class:'ask-form'},
    el('label',{class:'ask-sr',for:'ask-input'},'Your question for the guide'),
    el('div',{class:'ask-row'},input,send),
    el('p',{class:'ask-foot'},FOOTER.replace(/ Not a reviewer\.$/,' '),el('span',{class:'ask-nowrap'},'Not a reviewer.'),' ',privacy));
  const dialog=el('dialog',{class:'ask-panel',id:'topicllm-ask','aria-labelledby':'ask-title','aria-describedby':'ask-greeting'},
    el('header',{class:'ask-head'},title,close),scroll,form);
  document.body.append(dialog);

  let history=[],busy=false,op=null,ready=false,opener=null,closing=false,pressedBackdrop=false;

  const askButtons=()=>document.querySelectorAll('[data-ask]');
  const setExpanded=open=>{for(const b of askButtons()){b.setAttribute('aria-controls','topicllm-ask');b.setAttribute('aria-expanded',String(open));}};
  setExpanded(false);

  function showChips(list){
    chips.replaceChildren();
    for(const question of list){
      const b=el('button',{type:'button',class:'ask-chip'},question);
      b.disabled=busy;b.addEventListener('click',()=>ask(question));chips.append(b);
    }
    chips.hidden=!list.length;
  }
  showChips(STARTERS);

  function lockScroll(on){
    const root=document.documentElement;
    if(on){root.classList.toggle('ask-gutter',innerWidth>root.clientWidth);root.classList.add('ask-open');}
    else root.classList.remove('ask-open','ask-gutter');
  }
  function openPanel(from){
    if(dialog.open)return;
    opener=from||document.activeElement;closing=false;dialog.classList.remove('is-closing');
    lockScroll(true);
    if(typeof dialog.showModal==='function')dialog.showModal();else dialog.setAttribute('open','');
    setExpanded(true);
    // Keep the phone keyboard closed until the visitor chooses to type.
    (matchMedia('(max-width: 640px)').matches?title:input).focus({preventScroll:true});
  }
  function finishClose(){
    if(typeof dialog.close==='function'&&dialog.open)dialog.close();
    else if(dialog.hasAttribute('open')){dialog.removeAttribute('open');onClosed();}
  }
  function closePanel(){
    if(!dialog.open||closing)return;
    if(reducedMotion())return finishClose();
    closing=true;dialog.classList.add('is-closing');
    const done=event=>{
      if(event&&event.target!==dialog)return;
      clearTimeout(timer);dialog.removeEventListener('animationend',done);
      closing=false;dialog.classList.remove('is-closing');finishClose();
    };
    const timer=setTimeout(done,260);
    dialog.addEventListener('animationend',done);
  }
  function onClosed(){
    closing=false;dialog.classList.remove('is-closing');lockScroll(false);setExpanded(false);
    if(location.hash==='#ask')clearAskHash();
    const target=opener&&opener.isConnected&&opener!==document.body?opener:askButtons()[0];
    target?.focus?.({preventScroll:true});opener=null;
  }
  // Clear #ask so the same link can open the panel again.
  function clearAskHash(){try{window.history.replaceState(window.history.state,'',location.pathname+location.search);}catch{}}

  dialog.addEventListener('close',onClosed);
  dialog.addEventListener('cancel',event=>{event.preventDefault();closePanel();});
  close.addEventListener('click',closePanel);
  // A click that both starts and ends outside the panel box is a backdrop click.
  const outside=event=>{if(event.target!==dialog)return false;const r=dialog.getBoundingClientRect();return event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom;};
  dialog.addEventListener('pointerdown',event=>{pressedBackdrop=outside(event);});
  dialog.addEventListener('click',event=>{if(pressedBackdrop&&outside(event))closePanel();pressedBackdrop=false;});
  dialog.addEventListener('keydown',event=>{
    if(event.key==='Escape'&&typeof dialog.showModal!=='function'){event.preventDefault();closePanel();return;}
    if(event.key!=='Tab')return;
    const focusable=[...dialog.querySelectorAll('button:not([disabled]),a[href],textarea:not([disabled])')].filter(n=>n.getClientRects().length);
    if(!focusable.length)return;
    const first=focusable[0],last=focusable[focusable.length-1],active=document.activeElement;
    if(event.shiftKey&&(active===first||active===title||!dialog.contains(active))){event.preventDefault();last.focus();}
    else if(!event.shiftKey&&(active===last||!dialog.contains(active))){event.preventDefault();first.focus();}
  });

  document.addEventListener('click',event=>{
    const trigger=event.target instanceof Element&&event.target.closest('[data-ask]');
    if(!trigger||dialog.contains(trigger))return;
    event.preventDefault();openPanel(trigger);
  });
  addEventListener('hashchange',()=>{if(location.hash==='#ask')openPanel();});
  if(location.hash==='#ask')openPanel();

  input.addEventListener('input',()=>{input.style.height='auto';input.style.height=Math.min(input.scrollHeight,140)+'px';});
  input.addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.shiftKey&&!event.isComposing){event.preventDefault();form.requestSubmit();}});
  form.addEventListener('submit',event=>{event.preventDefault();const question=input.value;input.value='';input.style.height='';ask(question,true);});

  function setBusy(on){
    busy=on;send.disabled=on;log.setAttribute('aria-busy',String(on));
    for(const b of chips.querySelectorAll('button'))b.disabled=on;
  }
  function revealStart(node){scroll.scrollTop+=node.getBoundingClientRect().top-scroll.getBoundingClientRect().top-16;}
  function addNote(text){const note=el('div',{class:'ask-msg ask-msg--note'},el('p',{},text));log.append(note);scroll.scrollTop=scroll.scrollHeight;return note;}
  function addAnswer(result){
    const message=el('div',{class:'ask-msg ask-msg--guide'},hidden('The guide said: '));
    for(const paragraph of String(result.text||'').split(/\n\s*\n/))if(paragraph.trim())message.append(el('p',{},paragraph.trim()));
    // The server releases at most one validated source; it becomes the answer's link.
    const source=(Array.isArray(result.sources)?result.sources:[]).map(s=>({title:typeof s?.title==='string'?s.title:'',href:safeHref(s?.url)})).find(s=>s.title&&s.href);
    if(source)message.append(el('p',{class:'ask-source'},el('a',{href:source.href,target:'_blank',rel:'noopener'},source.title+' ↗')));
    log.append(message);
    if(Number.isInteger(result.remaining_session)&&result.remaining_session<=10)addNote(`${result.remaining_session} live questions left today.`);
    return message;
  }

  async function request(path,options={}){
    const response=await fetch(path,{credentials:'same-origin',cache:'no-store',...options});
    let body;try{body=await response.json();}catch{throw new Error('The guide could not connect.');}
    if(!response.ok)throw Object.assign(new Error(body?.error||'The guide is unavailable.'),{status:response.status,retryNewOperation:body?.retry_new_operation===true});
    return body;
  }
  async function startSession(){
    const config=await request('/api/config');
    if(!config.guideLive)throw new Error('The live guide is unavailable right now.');
    await request('/api/session');ready=true;
  }
  // The operation ID stays the same when an unchanged question is retried, so a
  // response that completed but was not delivered is recovered, not charged twice.
  async function post(operation){
    const call=()=>request(API,{method:'POST',headers:{'Content-Type':'application/json','X-Request-ID':operation.id},body:operation.payload,signal:AbortSignal.timeout?.(60000)});
    if(!ready)await startSession();
    try{return await call();}
    // An expired session is refused before any allowance is reserved, so one renewal is safe.
    catch(error){if(error.status!==401)throw error;ready=false;await startSession();return call();}
  }

  async function ask(raw,typed=false){
    const question=String(raw||'').trim();
    if(busy||!question)return;
    const recent=[];let size=0;
    for(let i=history.length-2;i>=0&&recent.length<6;i-=2){
      const pair=history.slice(i,i+2),chars=pair.reduce((n,m)=>n+m.content.length,0);
      if(size+chars>8500)break;recent.unshift(...pair);size+=chars;
    }
    const payload=JSON.stringify({question,history:recent,page});
    if(!op||op.payload!==payload)op={id:operationId(),payload};
    const previousChips=[...chips.querySelectorAll('button')].map(b=>b.textContent);
    showChips([]);setBusy(true);
    const asked=el('div',{class:'ask-msg ask-msg--user'},hidden('You asked: '),el('p',{},question));
    const typing=el('div',{class:'ask-typing'},hidden('The guide is writing an answer.'),el('i',{'aria-hidden':'true'}),el('i',{'aria-hidden':'true'}),el('i',{'aria-hidden':'true'}));
    log.append(asked,typing);scroll.scrollTop=scroll.scrollHeight;
    try{
      const result=await post(op);
      typing.remove();
      const answer=addAnswer(result);
      history.push({role:'user',content:question},{role:'assistant',content:String(result.text||'')});op=null;
      setBusy(false);
      showChips((Array.isArray(result.suggestions)?result.suggestions:[]).filter(s=>typeof s==='string'&&s.trim()).map(s=>s.trim()).slice(0,MAX_FOLLOW_UPS));
      revealStart(answer);
    }catch(error){
      typing.remove();asked.remove();
      if(error.retryNewOperation)op=null;
      if(typed&&!input.value.trim())input.value=question;
      const message=error.name==='TimeoutError'?'The request took too long. Send the same question again to recover a completed answer safely.'
        :error instanceof TypeError?'The guide could not connect. Check your connection and try again.':error.message;
      setBusy(false);addNote(message);showChips(previousChips);
    }finally{
      setBusy(false);
      if(dialog.open&&!matchMedia('(max-width: 640px)').matches)input.focus({preventScroll:true});
    }
  }
}

if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mount,{once:true});
else mount();
