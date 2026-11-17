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
 assert.equal(run.discovery_records+run.excluded_empty,rows.length);
 assert.equal(run.topics.reduce((n,t)=>n+t.count,run.outliers),run.discovery_records);
 for(const p of Object.keys(run.periods)){
  assert.equal(run.topics.reduce((n,t)=>n+t.period_counts[p],run.outlier_period_counts[p]+run.excluded_period_counts[p]),run.period_counts[p]);
 }
 assert.equal(Object.values(run.candidate_status_counts).reduce((a,b)=>a+b,0),1200);
 assert.equal(run.human_review_performed,false);assert.equal(run.classifier_validated,false);
 assert.equal(run.verification.selected_model_reload_verified,true);
});

test('every live example preserves its public source text and never uses a dissertation ID',async()=>{
 const base=new URL('../docs/data/trump/',import.meta.url);
 const rows=parseCSV(await readFile(new URL('corpus.csv',base),'utf8')).rows;
 const source=new Map(rows.map(r=>[r.post_id,r]));
 const live=JSON.parse(await readFile(new URL('live-examples.json',base)));
 for(const e of live.examples){assert.equal(e.id,'trump-'+e.post_id);assert.equal(e.text,source.get(e.post_id).tweet);}
 assert.ok(live.examples.length>=1024);assert.match(live.taxonomy_status,/Unvalidated/);
});

test('withdrawn public data and old wheels cannot fall through to assets',async()=>{
 const env={ASSETS:{fetch(){throw new Error('Withdrawn asset reached storage');}}};
 for(const path of ['/S4_liwc_output.csv','/data/reference_run/stage1_parameters.json','/data/study1/full.csv','/data/study1/discovery.csv','/data/live-examples.json','/validation/results.json','/downloads/topicllm_research-0.4.0-py3-none-any.whl']){
  const response=await worker.fetch(new Request('https://topicllm.dev'+path),env);
  assert.equal(response.status,410,path);
 }
});
