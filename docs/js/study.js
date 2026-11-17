import {parseCSV,escapeHTML as esc,toCSV,buildZip,downloadBlob} from './util.js';
import {sha256} from './research.js';
import {groupedBarChart} from './charts.js';
let study,demo,corpus,phase=0,counts;
const $=id=>document.getElementById(id);
const labels=['Discover patterns in real posts','Give a topic a useful name','Turn topics into meaningful themes','Apply themes to individual posts','Compare themes across time'];
const captions=[
 'Start with the Study 1 brand posts. A topic model groups similar language so you can inspect recurring ideas. Open a group to see the words behind it.',
 'A topic is initially a list of words and the posts behind it. Ask the LLM for several independent names, inspect the votes, and decide whether the proposed name describes the evidence.',
 'A topic is a statistical group; a theme is a human interpretation. The dissertation combined seven topics into five themes. This published map explains the decision researchers make at this stage.',
 'Once themes are defined, a classifier assigns each post to a theme or the residual category. Try a live example, then inspect whether the label fits.',
 'Prevalence is the share of posts assigned to a theme in each period. This chart shows the dissertation’s findings and illustrates the final output of the workflow.'
];
export async function loadStudy(){
 if(study)return {study,demo,corpus};
 const base=new URL('../data/',import.meta.url),get=async n=>{const r=await fetch(new URL(n,base));if(!r.ok)throw new Error(`Could not load ${n}.`);return r.text();};
 const [s,m,c]=await Promise.all([get('study.json'),get('study1/manifest.json'),get('study1/full.csv')]);
 demo=JSON.parse(m);if(await sha256(c)!==demo.files['full.csv'].sha256)throw new Error('Study 1 corpus checksum mismatch.');
 study=JSON.parse(s);corpus=parseCSV(c).rows;return {study,demo,corpus};
}
const goLive=()=>document.querySelector('[data-tab="live"]').click();
function renderPhase(){
 $('study-heading').textContent=labels[phase];$('study-explanation').textContent=captions[phase];
 document.querySelectorAll('[data-study-phase]').forEach((b,i)=>{b.setAttribute('aria-current',i===phase?'step':'false');b.classList.toggle('selected',i===phase);});
 $('study-back').disabled=phase===0;$('study-next').textContent=phase===4?'Start again':'Continue →';$('study-position').textContent=`${phase+1} of 5`;
 const body=$('study-content'),run=demo.reference_run;
 if(phase===0){
  body.innerHTML=`<div class="study-contrast"><div><span class="eyebrow">The study behind the demo</span><strong>11 <small>alcohol brands</small></strong><p>Original social media posts from January 2019–July 2021.</p><a href="../data/study1/full.csv" download>Download Study 1 ↗</a></div><div><span class="eyebrow">Recorded discovery</span><strong>${run.parameters.n_topics} <small>topics</small></strong><p>The model searched for patterns in the Study 1 example. It left ${(100*run.outliers/run.documents).toFixed(1)}% of texts ungrouped for researchers to review.</p><a href="../validation/">Inside the demo ↗</a></div></div><p class="note">Topic models and LLMs can vary across runs. This example shows the method in action.</p><details><summary>Explore the topic words</summary><div class="topic-map">${run.topics.map(t=>`<article><span class="topic-number">${Number(t.id)+1}</span><div><h3>${t.count} posts</h3><p>${t.words.map(esc).join(' · ')}</p></div></article>`).join('')}</div></details>`;
 }else if(phase===1){
  body.innerHTML=`<div class="reproduction-callout"><h3>Try a small voting experiment.</h3><p>Select one of the five recorded topics, request 1–20 independent names, and inspect the tally and raw responses. The dissertation used 5,000 queries per topic; a short interactive experiment shows the mechanism.</p><button class="btn primary" id="tour-live">Try naming votes →</button></div><div class="topic-map">${run.topics.map(t=>`<article><span class="topic-number">${Number(t.id)+1}</span><div><h3>Recorded topic ${Number(t.id)+1}</h3><p class="topic-words">${t.words.map(esc).join(' · ')}</p><p class="note">${t.count} posts in this group. A statistical topic has no approved human theme yet.</p></div></article>`).join('')}</div>`;
  $('tour-live').onclick=goLive;
 }else if(phase===2){
  const themes=[...new Set(study.topics.map(t=>t.theme))];
  body.innerHTML=`<div class="mapping-heading"><span>7 topics reported in the dissertation</span><span>5 researcher-defined themes</span></div><div class="theme-mapping">${themes.map((theme,index)=>`<div class="mapping-row"><div class="mapping-sources">${study.topics.filter(t=>t.theme===theme).map(t=>`<div><span>${String(study.topics.indexOf(t)+1).padStart(2,'0')}</span><p>${esc(t.name)}</p></div>`).join('')}</div><span class="mapping-arrow" aria-hidden="true">→</span><div class="mapping-target"><span class="mapping-index">${String(index+1).padStart(2,'0')}</span><h3>${esc(theme)}</h3></div></div>`).join('')}</div><p class="note">Dissertation Table 2, p. 165. This published example shows the human synthesis step. New discoveries need their own researcher review.</p>`;
 }else if(phase===3){
  body.innerHTML=`<div class="study-contrast"><div><span class="eyebrow">Try it on a study post</span><h3>Which theme fits?</h3><p>Search by brand, date or words. Ask OpenAI to classify a post using the five reported themes, then inspect its answer.</p><button class="btn primary" id="tour-live">Try a real post →</button></div><div><span class="eyebrow">The research checkpoint</span><h3>Validate before scaling.</h3><p>Compare predictions with independently annotated examples before classifying your research corpus. Review performance for every theme.</p><a href="../reproduce/">Give your agent the workflow ↗</a></div></div>`;
  $('tour-live').onclick=goLive;
 }else{
  body.innerHTML=`<div id="study-results" aria-live="polite"></div><div class="result-toolbar"><button class="btn" id="download-study">Download study evidence</button></div>`;
  $('download-study').onclick=download;if(counts)renderResults();else calculate();
 }
}
function calculate(){
 counts=Object.entries(study.periods).map(([period,[start,end]])=>{const rows=corpus.filter(r=>r.date>=start&&r.date<=end);return {period,start,end,records:rows.length,nonempty:rows.filter(r=>r.tweet.trim()).length};});
 renderResults();
}
function renderResults(){
 $('download-study').disabled=false;const outside=corpus.length-counts.reduce((s,r)=>s+r.records,0);
 $('study-results').innerHTML=`<p class="eyebrow">Reported findings · Study 1</p><div id="study-chart" class="chart-box"></div><details><summary>View the reported percentages</summary><div class="table-box"><table><caption>Reported theme prevalence (%), dissertation Table 3</caption><thead><tr><th>Theme</th><th>Pre</th><th>Peri</th><th>Post</th></tr></thead><tbody>${study.prevalence.map(r=>`<tr><th>${esc(r.theme)}</th>${['pre','peri','post'].map(k=>`<td>${r[k].toFixed(1)}%</td>`).join('')}</tr>`).join('')}</tbody></table></div></details><p class="note">These are the dissertation’s results. Your own run produces new estimates after theme review and classifier validation. <a href="../THOMAS-PRIMARY-2025.pdf#page=166">Read the original table ↗</a></p><details><summary>Inspect period definitions and counts</summary><div class="table-box"><table><caption>Study records by period, before classification</caption><thead><tr><th>Period</th><th>Dates</th><th>Records</th><th>With text</th></tr></thead><tbody>${counts.map(r=>`<tr><th>${esc(r.period)}</th><td>${r.start} to ${r.end}</td><td>${r.records.toLocaleString()}</td><td>${r.nonempty.toLocaleString()}</td></tr>`).join('')}</tbody></table></div><p>${outside} February 2020 records are outside the comparison periods. Text analysis excludes one blank record. <a href="../data/README.md">Technical data documentation ↗</a></p></details>`;
 groupedBarChart($('study-chart'),{groups:study.prevalence.map(r=>r.theme),series:['pre','peri','post'],values:study.prevalence.map(r=>['pre','peri','post'].map(k=>r[k]))});
}
function download(){downloadBlob('topicllm-study1-demonstration.zip',buildZip({'README.txt':'ORIGINAL STUDY 1 DATA / ILLUSTRATIVE RERUN\nOriginal brand data, recorded modern discovery, and separately identified dissertation results. Probabilistic methods and changing environments can produce different results. No Study 2 user records or invented human labels are included.\n','manifest.json':JSON.stringify(demo,null,2),'study1-full.csv':toCSV(corpus),'original-period-counts.csv':toCSV(counts),'reported-study-results.json':JSON.stringify(study,null,2)}));}
export async function initStudyTour(){try{await loadStudy();renderPhase();document.querySelectorAll('[data-study-phase]').forEach(b=>b.onclick=()=>{phase=Number(b.dataset.studyPhase);renderPhase();});$('study-back').onclick=()=>{phase=Math.max(0,phase-1);renderPhase();};$('study-next').onclick=()=>{phase=(phase+1)%5;renderPhase();};}catch(error){$('study-explanation').textContent=error.message;}}
let resize;addEventListener('resize',()=>{clearTimeout(resize);resize=setTimeout(()=>{if(phase===4&&counts&&$('study-chart'))renderResults();},120);});
