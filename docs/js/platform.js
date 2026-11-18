if(location.hostname==='jethomasphd.github.io'&&/^\/TopicLLM(?:\/|$)/.test(location.pathname))location.replace('https://topicllm.dev'+(location.pathname.replace(/^\/TopicLLM/,'')||'/')+location.search+location.hash);
/* Shared navigation and theme controls; no API calls or stored research data. */
import './welcome.js';
import './guide.js';
const menu=document.querySelector('[data-menu]'),nav=document.querySelector('#platform-nav');
if(menu&&nav){
 const close=()=>{menu.setAttribute('aria-expanded','false');nav.classList.remove('open');};
 menu.addEventListener('click',()=>{const open=menu.getAttribute('aria-expanded')!=='true';menu.setAttribute('aria-expanded',String(open));nav.classList.toggle('open',open);});
 nav.addEventListener('click',e=>{if(e.target.closest('a'))close();});
 document.addEventListener('keydown',e=>{if(e.key==='Escape'&&nav.classList.contains('open')){close();menu.focus();}});
}
document.querySelector('[data-platform-theme]')?.addEventListener('click',()=>{
 const current=document.documentElement.dataset.theme||(matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light');
 const next=current==='dark'?'light':'dark';document.documentElement.dataset.theme=next;
 try{localStorage.setItem('topicllm-theme',next);}catch{}
 document.dispatchEvent(new Event('topicllm-theme-change'));
});
const stages=[
 {role:'01 / COMPUTATION · RESEARCHER-DESIGNED INPUTS',title:'Find structure in the corpus.',description:'MiniLM embeddings, UMAP and HDBSCAN produce candidate topics. The campaign search evaluates 1,200 candidate settings. Researchers inspect coherence, coverage and original posts before adopting a solution; the numerical winner remains preserved. The observed topic count is a result, not a target.',artifacts:['all_iteration_results.json','topics_for_naming.csv','fitted_model.pkl + provenance hashes']},
 {role:'02 / MODEL QUERIES · RESEARCHER INTERPRETATION',title:'Name by repeated independent votes.',description:'The LLM proposes a name from each topic’s representative words. Repeated queries produce a distribution of candidate names. The modal label is a proposal, and disagreement remains visible. Recorded campaign application: 500 completed votes per topic; interactive demonstration: 1–20.',artifacts:['vote_log.csv','vote_tallies.csv','raw responses + model + token usage']},
 {role:'03 / HUMAN DECISION · AGENT PREPARES EVIDENCE',title:'Researchers decide what themes mean.',description:'Two actual researchers review topic words, sampled posts and naming evidence, then agree on the theme map. An agent can assemble the packet. It cannot supply reviewer identities or approve its own interpretation. Research execution pauses at this gate.',artifacts:['topic review packet','approved theme_map.csv','review record bound to evidence hashes']},
 {role:'04 / BENCHMARK GATE · THEN CORPUS SCALING',title:'Validate before labeling everything.',description:'Select between Boolean and LLM classification on development annotations. Test the frozen choice on untouched presidential examples. Inspect per-theme errors and obtain actual researcher acceptance before labeling the target corpus.',artifacts:['classifier_selection.json','validation_report.json + human acceptance','target labels with IDs and provenance']},
 {role:'05 / STATISTICAL COMPUTATION · SCIENTIFIC REVIEW',title:'Make every denominator inspectable.',description:'Count each accepted theme across the 26,239 presidential posting events and divide by that complete denominator. Include the residual and zero-count themes. The primary application reports overall shares without period comparisons.',artifacts:['theme_counts.csv','estimand.json','classifications + environment + API ledger']}
];
const buttons=[...document.querySelectorAll('[data-method-stage]')];
function selectStage(index){const step=stages[index];buttons.forEach((b,i)=>b.setAttribute('aria-pressed',String(i===index)));document.querySelector('#method-role').textContent=step.role;document.querySelector('#method-title').textContent=step.title;document.querySelector('#method-description').textContent=step.description;const list=document.querySelector('#method-artifacts');list.replaceChildren(...step.artifacts.map(value=>{const line=document.createElement('code');line.textContent='↳ '+value;return line;}));}
buttons.forEach((button,index)=>{button.addEventListener('click',()=>selectStage(index));button.addEventListener('keydown',e=>{if(['ArrowRight','ArrowLeft','Home','End'].includes(e.key)){e.preventDefault();let next=e.key==='Home'?0:e.key==='End'?4:(index+(e.key==='ArrowRight'?1:4))%5;buttons[next].focus();selectStage(next);}});});
