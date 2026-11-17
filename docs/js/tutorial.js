import {initLiveDemo} from './live-demo.js';
import {downloadText} from './util.js';
const $=id=>document.getElementById(id);
const node=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
let data,phase=0,selected='0';const draft=new Map();
function tab(name){for(const b of document.querySelectorAll('[data-tab]')){const active=b.dataset.tab===name;b.setAttribute('aria-pressed',String(active));b.classList.toggle('active',active);}for(const id of ['walkthrough','live'])$('tab-'+id).hidden=id!==name;}
document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>tab(b.dataset.tab));
function live(){tab('live');$('live-topic')?.focus();}
const explain=[
 ['Discover','Find groups of similar language.','The Python run compares candidate models and keeps the one with the highest coherence. Explore its words and posts. A coherent group is a starting point for interpretation—not a scientific conclusion.'],
 ['Name','Ask for a name. Keep the disagreement.','Give the model a topic’s representative words and collect several independent naming responses. The most frequent name is a proposal. A tally shows variation; it does not establish truth.'],
 ['Synthesize','Decide what the topics mean together.','Researchers read the posts in context and decide which topics express a shared theme. Try a draft below: use the same theme name to group related topics. Your draft stays in this page until you download it.'],
 ['Classify','Test an interpretation before scaling it.','Once researchers define a taxonomy, a classifier can assign posts to its categories. First test it against independently annotated examples. A convincing individual response is not enough.'],
 ['Estimate','Make the denominator visible.','Explore where this model assigns posts across the three periods. This chart describes topic assignments, not validated theme prevalence. Research estimates come after human synthesis and classifier validation.']
];
function note(text){return node('p',text,'tutorial-note');}
function action(text,fn){const b=node('button',text,'btn primary');b.type='button';b.onclick=fn;return b;}
function topicSelect(host,onchange,includeCoverage=false){const label=node('label','Choose a recorded topic');label.htmlFor='topic-inspector';const select=node('select');select.id='topic-inspector';for(const t of data.topics)select.add(new Option(`Topic ${t.id} · ${t.words.slice(0,3).join(' / ')}`,String(t.id)));if(includeCoverage){select.add(new Option('Outliers · not assigned to a topic','-1'));select.add(new Option('No tokens after preprocessing','excluded'));}if(![...select.options].some(o=>o.value===selected))selected=String(data.topics[0]?.id??'');select.value=selected;select.onchange=()=>{selected=select.value;onchange(select.value);};host.append(label,select);return select;}
function words(topic){const group=node('div',undefined,'topic-words');for(const w of topic.words)group.append(node('span',w));return group;}
function post(record){const q=node('blockquote',undefined,'source-post');q.append(node('small',`${record.date} · ${record.post_id}${record.is_retweet==='t'?' · Retweet':''}`),node('p',record.tweet));return q;}
function render(){
 if(!data)return;const [name,title,intro]=explain[phase];$('stage-position').textContent=`STEP 0${phase+1} / ${name.toUpperCase()}`;$('stage-title').textContent=title;$('stage-intro').textContent=intro;
 document.querySelectorAll('[data-phase]').forEach(b=>b.setAttribute('aria-pressed',String(Number(b.dataset.phase)===phase)));
 const host=$('stage-content');host.replaceChildren();$('stage-back').disabled=phase===0;$('stage-next').textContent=phase===4?'Fork + run ↗':'Continue →';
 if(phase===0){
  const metrics=node('div',undefined,'tutorial-metrics');for(const [value,label] of [[data.topics.length,'discovered topics'],[data.discovery_records.toLocaleString(),'modeled posts'],[(100*data.outliers/data.discovery_records).toFixed(1)+'%','model outliers']]){const box=node('div',undefined,'tutorial-metric');box.append(node('strong',String(value)),node('span',label));metrics.append(box);}host.append(metrics);
  const distribution=node('div',undefined,'topic-distribution');distribution.setAttribute('role','img');distribution.setAttribute('aria-label',`${data.discovery_records-data.outliers} posts grouped; ${data.outliers} model outliers.`);for(const t of [...data.topics,{id:-1,count:data.outliers}]){const bar=node('span',undefined,t.id===-1?'outlier':'');bar.style.width=(100*t.count/data.discovery_records)+'%';bar.title=`${t.id===-1?'Outliers':'Topic '+t.id}: ${t.count.toLocaleString()} posts`;distribution.append(bar);}host.append(distribution);
  const sizes=data.topics.map(t=>t.count).sort((a,b)=>b-a);
  if(sizes[0]/(data.discovery_records-data.outliers)>.9)host.append(note(`Read the imbalance: one broad group holds ${sizes[0].toLocaleString()} posts; the others hold ${sizes.slice(1).map(n=>n.toLocaleString()).join(' and ')}. Coherence gives each topic equal weight, so small similar groups can lift the score. Inspect these groups before treating them as meaningful categories.`));
  const browser=node('div',undefined,'topic-browser'),detail=node('div');const update=id=>{const t=data.topics.find(t=>String(t.id)===id);detail.replaceChildren(words(t),node('p',`${t.count.toLocaleString()} posts in this group. The examples below are seeded samples, not handpicked proof.`, 'note'));for(const r of t.examples)detail.append(post(r));};topicSelect(browser,update);browser.append(detail);host.append(browser);update(selected);
  host.append(note(`The source corpus contains ${data.source_records.toLocaleString()} posts. ${data.excluded_empty.toLocaleString()} have no tokens after preprocessing and stay outside discovery; all remain in the source download. Outliers are modeled posts that HDBSCAN did not assign to a group.`));
 }
 if(phase===1){
  host.append(node('h3','Words → candidate names → researcher interpretation'));
  const t=data.topics.find(t=>String(t.id)===selected)||data.topics[0];host.append(words(t),note('Independent calls sample one model’s responses. Similar answers can reflect shared model bias; different wording can describe the same idea. The historical protocol used 5,000 votes per topic. This live lab offers 1–20 for a small experiment.'));
  host.append(action('Collect votes in the live lab →',()=>{if($('live-topic'))$('live-topic').value=String(t.id);$('live-topic')?.dispatchEvent(new Event('change'));live();}));
 }
 if(phase===2){
  for(const t of data.topics){const row=node('div',undefined,'map-row'),label=node('label',`Topic ${t.id} · ${t.count.toLocaleString()} posts`),small=node('small',t.words.slice(0,5).join(', '));label.htmlFor='theme-'+t.id;label.append(small);const input=node('input');input.id='theme-'+t.id;input.maxLength=100;input.placeholder='Your candidate theme';input.value=draft.get(t.id)||'';input.oninput=()=>draft.set(t.id,input.value);row.append(label,input);host.append(row);}
  host.append(note('A theme needs a definition, inclusion/exclusion rules and evidence from posts—not just a name. In research, two actual researchers review this map and its domain literature. An agent can prepare the evidence; it cannot approve the interpretation.'));
  host.append(action('Download my draft map',()=>downloadText('topicllm-trump-draft-map.json',JSON.stringify({mode:'visitor-learning-draft',dataset:data.dataset,input_sha256:data.input_sha256,human_review_performed:false,research_approval:false,created_at:new Date().toISOString(),map:data.topics.map(t=>({topic:t.id,words:t.words,proposed_theme:draft.get(t.id)||''}))},null,2),'application/json')));
 }
 if(phase===3){
  const flow=node('div',undefined,'journey');for(const text of ['Define the theme','Annotate a benchmark','Inspect errors','Validate before scaling'])flow.append(node('span',text));host.append(flow,node('h3','A practice category is not a research finding.'),node('p','The live lab uses a fixed set of broad practice categories so you can inspect the mechanics of classification. They are separate from your draft map. No final Trump taxonomy or independently validated classifier is bundled.'),action('Inspect a live classification →',live),note('The Python workflow requires a current two-researcher review record and an independent benchmark. Overall agreement must exceed the configured threshold (default 85%), and every theme needs positive benchmark support and nonzero sensitivity. Researchers must also assess per-theme precision, recall and the acceptability of errors.'));
 }
 if(phase===4){
  const detail=node('div');topicSelect(host,id=>chart(detail,id),true);host.append(detail);chart(detail,selected);
  host.append(note('Each bar uses all source posts in that period as its denominator. Outliers and texts with no modeled tokens remain separate selectable outcomes. These are descriptive assignments from one fitted model; they are not human-approved theme prevalence or evidence of a causal effect.'));
  host.append(node('h3','For research: validate labels, then estimate.'),node('p','The package counts researcher-approved classifier labels, retains denominators and exclusions, and compares proportions under declared assumptions. Repeated posts, retweets and time dependence within one account require methodological care. A small p-value alone cannot settle the interpretation.'));
 }
}
function chart(host,id){host.replaceChildren();const group=id==='excluded'?data.excluded_period_counts:id==='-1'?data.outlier_period_counts:data.topics.find(t=>String(t.id)===id).period_counts;for(const [key,period] of Object.entries(data.periods)){const count=group[key]||0,den=data.period_counts[key],pct=100*count/den;const row=node('div',undefined,'period-row'),label=node('div',undefined,'period-label');label.append(node('strong',{campaign:'Campaign',transition:'Transition',presidency:'Presidency through archive end'}[key]),node('span',pct.toFixed(2)+'%'));const track=node('div',undefined,'period-track'),bar=node('span');bar.style.width=pct+'%';track.append(bar);row.append(label,track,node('small',`${count.toLocaleString()} / ${den.toLocaleString()} posts · ${period.join(' → ')}`));host.append(row);}}
document.querySelectorAll('[data-phase]').forEach(b=>b.onclick=()=>{phase=Number(b.dataset.phase);render();});$('stage-back').onclick=()=>{phase=Math.max(0,phase-1);render();};$('stage-next').onclick=()=>{if(phase===4){location.href='../reproduce/';return;}phase++;render();};
try{const r=await fetch('../data/trump/reference-run.json');if(!r.ok)throw new Error('The recorded run could not be loaded.');data=await r.json();selected=String(data.topics[0]?.id??'0');render();}catch(e){$('stage-title').textContent='The walkthrough is temporarily unavailable.';$('stage-intro').textContent=e.message+' The corpus and local execution guide remain available.';$('stage-next').disabled=true;}
await initLiveDemo();if(location.hash==='#live')tab('live');
