import {parseCSV, escapeHTML as esc, toCSV, buildZip, downloadBlob} from './util.js';
import {estimatePrevalence, sha256} from './research.js';
import {groupedBarChart} from './charts.js';

let study, demo, corpus, result, phase=0;
const $ = id => document.getElementById(id);
const labels=['Discover topics','Name the topics','Review the themes','Classify the corpus','Compare periods'];
const captions=[
  'The dissertation reported seven topics. This exercise starts with seven categories assigned from the synthetic generator’s campaigns; it does not claim to rediscover the original model.',
  'The original study queried GPT-4o 5,000 times per topic and selected the most frequent label. These names are transcribed from Table 2. Original vote counts and ballots are not available here.',
  'Researchers interpreted the topic evidence and agreed on five broader themes. Two social-promotion topics and two sports topics were combined. For a new study, reviewers must make and document their own decisions.',
  'Every synthetic post has a label supplied by its generator. This lets you check calculations against known answers. It does not measure an LLM’s agreement with human judgment.',
  'Recalculate prevalence from all 5,872 synthetic records. The generator’s counts were chosen to match the dissertation’s rounded percentages. The calculated z statistics are synthetic results, not recovered historical tests.'
];

export async function loadStudy() {
  if (study) return {study,demo,corpus};
  const base = new URL('../data/',import.meta.url);
  const get=async n=>{const r=await fetch(new URL(n,base));if(!r.ok)throw new Error(`Could not load ${n}. Reload when your connection is available.`);return r.text();};
  const [s,d,c]=await Promise.all([get('study.json'),get('study-demo.json'),get('demonstration_corpus.csv')]);
  const parsed=JSON.parse(d);
  if(await sha256(c)!==parsed.corpus_sha256)throw new Error('Synthetic corpus checksum mismatch. The demo cannot be verified.');
  study=JSON.parse(s);demo=parsed;corpus=parseCSV(c).rows;
  return {study,demo,corpus};
}

function renderPhase() {
  $('study-heading').textContent=labels[phase];
  $('study-explanation').textContent=captions[phase];
  document.querySelectorAll('[data-study-phase]').forEach((b,i)=>{b.setAttribute('aria-current',i===phase?'step':'false');b.classList.toggle('selected',i===phase);});
  $('study-back').disabled=phase===0;
  $('study-next').textContent=phase===4?'Start again':'Continue →';
  $('study-position').textContent=`${phase+1} of 5`;
  const b=$('study-content');
  if(phase===0){
    b.innerHTML=`<div class="study-contrast"><div><span class="eyebrow">Reported in the dissertation</span><strong>7 <small>topics</small></strong><p>c<sub>v</sub> = 0.768 · maximum-topic setting 23<br>UMAP 15 / 4 / 0.01 · HDBSCAN minimum 20</p><a href="../THOMAS-PRIMARY-2025.pdf#page=163" target="_blank">Read the original result, p. 163 ↗</a></div><div><span class="eyebrow">This synthetic exercise</span><strong>7 <small>assigned categories</small></strong><p>Known campaigns reproduce the seven-to-five structure. No fitted coherence score is claimed.</p><a href="../audit/">Different data, different discovered topics ↗</a></div></div><p class="note">The maximum-topic setting is a ceiling. It is not the number of topics the model must return.</p>`;
  }else if(phase===2){
    const themes=[...new Set(study.topics.map(t=>t.theme))];
    b.innerHTML=`<div class="mapping-heading"><span>7 reported topics</span><span>5 interpreted themes</span></div><div class="theme-mapping">${themes.map((theme,index)=>`<div class="mapping-row"><div class="mapping-sources">${study.topics.filter(t=>t.theme===theme).map(t=>`<div><span>${String(study.topics.indexOf(t)+1).padStart(2,'0')}</span><p>${esc(t.name)}</p></div>`).join('')}</div><span class="mapping-arrow" aria-hidden="true">→</span><div class="mapping-target"><span class="mapping-index">${String(index+1).padStart(2,'0')}</span><h3>${esc(theme)}</h3></div></div>`).join('')}</div><p class="note">Reported topic-to-theme relationships from dissertation Table 2, p. 165. The demonstration uses assigned categories; it does not recover the original model or historical reviewer decisions.</p>`;
  }else if(phase===1){
    b.innerHTML=`<div class="topic-map">${study.topics.map((t,i)=>`<article><span class="topic-number">${String(i+1).padStart(2,'0')}</span><div><h3>${esc(t.name)}</h3>${phase===1?`<p class="topic-words">${t.words.map(esc).join(' · ')}</p>`:`<p class="theme-link">→ ${esc(t.theme)}</p>`}<details><summary>Inspect a synthetic example</summary><p>${esc(example(t.id))}</p><p class="note">Generated example; not a dissertation tweet or historical model assignment.</p></details></div></article>`).join('')}</div><p class="note">Names and representative words: dissertation Table 2, p. 165. Numbers 01–07 indicate display order.</p>`;
  }else if(phase===3){
    const n=demo.rows.filter(r=>r.topic===-1).length;
    b.innerHTML=`<div class="study-contrast"><div><span class="eyebrow">Complete synthetic corpus</span><strong>5,872 <small>posts</small></strong><p>All posts receive one of five theme labels, or the residual “does not fit” label. ${n.toLocaleString()} synthetic posts belong to that residual category.</p></div><div><span class="eyebrow">For an actual research study</span><h3>Validate each theme.</h3><p>Use independently coded, held-out documents. Inspect precision, sensitivity and the confusion matrix. Overall accuracy can conceal a failure to detect rare themes.</p></div></div><p class="note">The bundled 250-row benchmark uses generated truth, despite its legacy column name <code>human_label</code>. It is a software exercise, not a human-validation dataset.</p>`;
  }else{
    b.innerHTML=`<div class="result-toolbar"><button class="btn primary" id="calculate-study">Calculate from synthetic records</button><button class="btn" id="download-study" disabled>Download evidence bundle</button></div><div id="study-results" aria-live="polite"><p>Run the calculation to compare synthetic results with the reported table.</p></div>`;
    $('calculate-study').onclick=calculate;
    $('download-study').onclick=download;
    if(result)renderResults();
  }
}
function example(topic){const id=demo.rows.find(r=>r.topic===topic)?.post_id;return corpus.find(r=>r.post_id===id)?.tweet||'No example available.';}
function calculate(){
  const lookup=new Map(demo.rows.map(r=>[r.post_id,r]));
  const classified=corpus.map(r=>({...r,theme:lookup.get(r.post_id).theme,status:'synthetic_truth'}));
  result=estimatePrevalence(classified,study.prevalence.map(r=>r.theme),study.periods);
  renderResults();
}
function renderResults(){
  $('download-study').disabled=false;
  const matches=result.prevRows.every(r=>['pre','peri','post'].every(p=>Number(r[`${p}_pct`].toFixed(1))===study.prevalence.find(t=>t.theme===r.theme)[p]));
  $('study-results').innerHTML=`<div class="verified-result"><span aria-hidden="true">✓</span><div><h3>${matches?'All 15 rounded percentages match Table 3.':'The calibration differs from Table 3.'}</h3><p>Calculated from synthetic labels · ${result.outsidePeriods} February 2020 posts excluded from period comparisons · α = 0.05 / 15</p></div></div><div id="study-chart" class="chart-box"></div><div class="table-box"><table><caption>Synthetic percentages, with dissertation percentages in parentheses</caption><thead><tr><th scope="col">Theme</th><th scope="col">Pre</th><th scope="col">Peri</th><th scope="col">Post</th></tr></thead><tbody>${result.prevRows.map(r=>`<tr><th scope="row">${esc(r.theme)}</th>${['pre','peri','post'].map(p=>`<td>${r[`${p}_pct`].toFixed(1)}% <span class="muted">(${study.prevalence.find(t=>t.theme===r.theme)[p].toFixed(1)}%)</span></td>`).join('')}</tr>`).join('')}</tbody></table></div><details class="stat-detail"><summary>Inspect calculated counts and statistical tests</summary><div class="table-box"><table><thead><tr><th>Theme</th><th>Comparison</th><th>Count A / N</th><th>Count B / N</th><th>z</th><th>p</th><th>Bonferroni</th></tr></thead><tbody>${result.testRows.map(r=>`<tr><td>${esc(r.theme)}</td><td>${r.comparison}</td><td>${r.k_a} / ${r.n_a}</td><td>${r.k_b} / ${r.n_b}</td><td>${r.z?.toFixed(3)??'—'}</td><td>${r.p?.toPrecision(3)??'—'}</td><td>${r.significant_bonferroni?'Significant':'Not significant'}</td></tr>`).join('')}</tbody></table></div></details><p class="note">Synthetic period sizes are calibration choices: 1,707 pre, 806 peri and 3,106 post. They have not been verified as the original study denominators. Matching rounded percentages does not recover the original observations. <a href="../THOMAS-PRIMARY-2025.pdf#page=166">View unchanged Table 3 ↗</a></p>`;
  groupedBarChart($('study-chart'),{groups:result.prevRows.map(r=>r.theme),series:['pre','peri','post'],values:result.prevRows.map(r=>['pre','peri','post'].map(p=>r[`${p}_pct`]))});
}
function download(){
  const files={
    'README.txt':'CALIBRATED SYNTHETIC RECONSTRUCTION\nNo original tweets, fitted model, human benchmark or historical LLM ballots are included. Seven categories are assigned from generator campaigns. Prevalence is computed from synthetic truth.\nSource: Thomas (2025), Chapter 4, pp.163–166.\n',
    'manifest.json':JSON.stringify({mode:demo.mode,corpus_sha256:demo.corpus_sha256,assignment_method:demo.assignment_method,source:study.source,generated_at:new Date().toISOString()},null,2),
    'reported-study.json':JSON.stringify(study,null,2),
    'synthetic-assignments.csv':toCSV(demo.rows),
    'synthetic-prevalence.csv':toCSV(result.prevRows),
    'synthetic-tests.csv':toCSV(result.testRows),
  };
  downloadBlob('topicllm-synthetic-study.zip',buildZip(files));
}
export async function initStudyTour(){
  try{
    await loadStudy();renderPhase();
    document.querySelectorAll('[data-study-phase]').forEach(b=>b.onclick=()=>{phase=Number(b.dataset.studyPhase);renderPhase();});
    $('study-back').onclick=()=>{phase=Math.max(0,phase-1);renderPhase();};
    $('study-next').onclick=()=>{phase=(phase+1)%5;renderPhase();};
  }catch(e){$('study-explanation').textContent=e.message;}
}

let chartResize;
addEventListener('resize',()=>{clearTimeout(chartResize);chartResize=setTimeout(()=>{if(phase===4&&result&&$('study-chart'))renderResults();},120);});
