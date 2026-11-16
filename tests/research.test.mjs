import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {canonicalLabel,validateBenchmark,estimatePrevalence,scoreLabels,NONE,INVALID} from '../docs/js/research.js';
import {parseCSV,toCSV} from '../docs/js/util.js';
import {preprocessDoc,buildStopwords} from '../docs/js/preprocess.js';
import {callWithRetries} from '../docs/js/llm.js';

test('invalid model text cannot become a substantive theme',()=>{
  for(const raw of ['Not Sports','Sports or Gaming','I cannot classify this','']) assert.equal(canonicalLabel(raw,['Sports','Gaming']).label,INVALID);
  assert.equal(canonicalLabel('2',['Sports','Gaming']).label,'Gaming');
  assert.equal(canonicalLabel('1. Sports.',['Sports','Gaming']).label,'Sports');
});
test('outages reject rather than fabricate a residual label or naming vote',async()=>{
  await assert.rejects(()=>callWithRetries(async()=>{throw new Error('outage');},1),/outage/);
});

test('cancelling a rate-limit wait stops without further requests',async()=>{
  const controller=new AbortController();
  controller.abort();
  let calls=0;
  await assert.rejects(()=>callWithRetries(async()=>{
    calls++;
    const error=new Error('rate limited');
    error.retryAfterMs=60000; error.signal=controller.signal;
    throw error;
  }),{name:'AbortError'});
  assert.equal(calls,1);
});
test('empty and unknown-label benchmarks cannot pass validation',()=>{
  assert.throws(()=>validateBenchmark([],['Sports']),/empty/);
  assert.throws(()=>validateBenchmark([{tweet:'abc',human_label:'Other'}],['Sports']),/outside/);
  const score=scoreLabels(['Sports',NONE],[NONE,NONE],['Sports',NONE]);
  assert.equal(score.per_label.Sports.recall,0);
});
test('CSV rejects ambiguous structure and preserves quoted content',()=>{
  assert.throws(()=>parseCSV('a,a\n1,2'),/unique/);
  assert.throws(()=>parseCSV('a,b\n1,2,3'),/column/);
  assert.throws(()=>parseCSV('a\n"unfinished'),/unclosed/);
  const data=[{text:'hello, "world"\nagain',date:'2020-01-01'}];
  assert.deepEqual(parseCSV(toCSV(data)).rows,data);
});
test('missing source text is never embedded as the word null',()=>{
  assert.equal(preprocessDoc(null,buildStopwords('')),'');
  assert.equal(preprocessDoc(undefined,buildStopwords('')),'');
});
test('synthetic reconstruction matches all 15 published rounded prevalences with increase-positive z',async()=>{
  const dir=new URL('../docs/data/',import.meta.url);
  const study=JSON.parse(await readFile(new URL('study.json',dir)));
  const demo=JSON.parse(await readFile(new URL('study-demo.json',dir)));
  const corpus=parseCSV(await readFile(new URL('demonstration_corpus.csv',dir),'utf8')).rows;
  const truth=new Map(demo.rows.map(r=>[r.post_id,r]));
  const result=estimatePrevalence(corpus.map(r=>({...r,theme:truth.get(r.post_id).theme})),study.prevalence.map(r=>r.theme),study.periods);
  assert.equal(new Set(demo.rows.filter(r=>r.topic>=0).map(r=>r.topic)).size,7);
  assert.equal(result.outsidePeriods,253);
  for(const row of result.prevRows) for(const p of ['pre','peri','post']) assert.equal(Number(row[`${p}_pct`].toFixed(1)),study.prevalence.find(t=>t.theme===row.theme)[p]);
  const delivery=result.testRows.find(r=>r.theme===study.prevalence[0].theme && r.comparison==='pre vs peri');
  assert.ok(Math.abs(delivery.z-6.02581055)<1e-7);
  assert.equal(result.testRows.length,15);
  assert.equal(result.testRows.filter(r=>r.significant_bonferroni).length,8);
});
test('inference refuses unresolved labels, overlaps and invalid dates',()=>{
  const rows=[{date:'2020-01-01',theme:'Sports'},{date:'2020-02-01',theme:NONE}];
  const periods={a:['2020-01-01','2020-01-31'],b:['2020-02-01','2020-02-28']};
  assert.throws(()=>estimatePrevalence([{...rows[0],theme:INVALID},rows[1]],['Sports'],periods),/Resolve/);
  assert.throws(()=>estimatePrevalence(rows,['Sports'],{a:['2020-01-01','2020-02-01'],b:['2020-02-01','2020-03-01']}),/overlap/);
  assert.throws(()=>estimatePrevalence([{...rows[0],date:'2020-02-30'},rows[1]],['Sports'],periods),/invalid dates/);
});
