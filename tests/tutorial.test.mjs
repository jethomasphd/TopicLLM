import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {parseCSV,toCSV} from '../docs/js/util.js';
import worker from '../worker/index.js';

test('CSV preserves string identifiers and quoted multiline text',()=>{
 const records=[{post_id:'1234567890123456789',tweet:'hello, "world"\nagain'}];
 assert.deepEqual(parseCSV(toCSV(records)).rows,records);
 for(const bad of ['a,a\n1,2','a,b\n1,2,3','a\n"unfinished'])assert.throws(()=>parseCSV(bad));
});

test('the public tutorial accounts for every source record exactly once',async()=>{
 const base=new URL('../docs/data/trump/',import.meta.url);
 const bytes=await readFile(new URL('corpus.csv',base));
 const manifest=JSON.parse(await readFile(new URL('manifest.json',base)));
 const run=JSON.parse(await readFile(new URL('reference-run.json',base)));
 assert.equal(createHash('sha256').update(bytes).digest('hex'),manifest.files['corpus.csv'].sha256);
 const rows=parseCSV(bytes.toString('utf8')).rows;
 assert.equal(rows.length,34416);assert.equal(new Set(rows.map(r=>r.post_id)).size,34416);
 assert.equal(rows[0].date,'2015-06-16');assert.equal(rows.at(-1).date,'2021-01-08');
 const discovery=rows.filter(r=>r.date>='2015-06-16'&&r.date<='2016-11-08');
 const target=rows.filter(r=>r.date>='2017-01-20'&&r.date<='2021-01-08');
 assert.equal(run.schema_version,2);
 assert.equal(run.archive_records,rows.length);
 assert.equal(run.source_records,discovery.length);assert.equal(discovery.length,7805);
 assert.equal(run.target_records,target.length);assert.equal(target.length,26239);
 assert.equal(run.discovery_records+run.excluded_empty,discovery.length);
 assert.equal(run.topics.reduce((n,t)=>n+t.count,run.outliers),run.discovery_records);
 const assignments=parseCSV(await readFile(new URL('campaign/assignments.csv',base),'utf8')).rows;
 const exclusions=parseCSV(await readFile(new URL('campaign/excluded.csv',base),'utf8')).rows;
 const ids=[...assignments,...exclusions].map(r=>r.post_id);
 assert.equal(ids.length,new Set(ids).size);
 assert.deepEqual(new Set(ids),new Set(discovery.map(r=>r.post_id)));
 assert.equal(run.verification.candidate_ceilings,1200);
 if(run.prevalence){
  assert.equal(run.human_review_performed,true);assert.equal(run.prevalence.reduce((n,r)=>n+Number(r.documents),0),target.length);
  if(!run.classifier_validated){assert.equal(run.demonstration_exception?.decision,'continue_unvalidated_demonstration');assert.equal(run.estimand?.model_mode,'unvalidated-demonstration');assert.equal(run.estimand.classifier_validated,false);assert.equal(run.validation.gate_passed,false);}
 }
 assert.equal(run.verification.selected_model_reload_verified,true);
});

test('every live example preserves its public source text and never uses a dissertation ID',async()=>{
 const base=new URL('../docs/data/trump/',import.meta.url);
 const rows=parseCSV(await readFile(new URL('corpus.csv',base),'utf8')).rows;
 const source=new Map(rows.map(r=>[r.post_id,r]));
 const live=JSON.parse(await readFile(new URL('live-examples.json',base)));
 for(const e of live.examples){assert.equal(e.id,'trump-'+e.post_id);assert.equal(e.text,source.get(e.post_id).tweet);}
 assert.ok(live.examples.length>=1024);assert.match(live.taxonomy_status,/unvalidated/i);
 assert.deepEqual(new Set(live.themes),new Set(Object.keys(live.codebook.themes)));
 const run=JSON.parse(await readFile(new URL('reference-run.json',base)));
 assert.equal(run.human_review_performed,true);assert.deepEqual(live.codebook,run.codebook);
 const codebook=await readFile(new URL('campaign/codebook.json',base));
 assert.equal(createHash('sha256').update(codebook).digest('hex'),live.codebook_sha256);
});

test('withdrawn public data and old wheels cannot fall through to assets',async()=>{
 const env={ASSETS:{fetch(){throw new Error('Withdrawn asset reached storage');}}};
 for(const path of ['/S4_liwc_output.csv','/data/reference_run/stage1_parameters.json','/data/study1/full.csv','/data/study1/discovery.csv','/data/live-examples.json','/validation/results.json','/downloads/topicllm_research-0.4.0-py3-none-any.whl','/data/trump/campaign/development_annotations.csv','/data/trump/campaign/evaluation_annotations.csv','/data/trump/campaign/evaluation_predictions.csv','/data/trump/campaign/development_annotations.review.json','/data/trump/campaign/development_predictions.csv']){
  const response=await worker.fetch(new Request('https://topicllm.dev'+path),env);
  assert.equal(response.status,410,path);
 }
});

test('superseded working manuscripts redirect while the protected original remains available',async()=>{
 const env={ASSETS:{fetch:async()=>new Response('original source')}};
 for(const name of ['TopicLLM_Methods_Revised_2026-11-16.pdf','TopicLLM_Methods_2026-11-17.pdf','TopicLLM_Methods_2026-11-18.pdf','TopicLLM_Methods_2026-11-19.pdf']){
  const response=await worker.fetch(new Request('https://topicllm.dev/preprints/'+name),env);
  assert.equal(response.status,302);assert.equal(response.headers.get('Location'),'https://topicllm.dev/preprints/TopicLLM_Methods_2026-11-20.pdf');
 }
 const original=await worker.fetch(new Request('https://topicllm.dev/preprints/Thomas_et_al_Methods_Coherence-Optimized_Topic_Modeling.pdf'),env);
 assert.equal(await original.text(),'original source');
});
