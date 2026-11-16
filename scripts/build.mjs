import {mkdir, cp, readFile, writeFile, stat} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const manifest = JSON.parse(await readFile(path.join(root,'source-integrity.json'),'utf8'));
for (const file of manifest.files) {
  const bytes = await readFile(path.join(root,file.path));
  if (createHash('sha256').update(bytes).digest('hex') !== file.sha256) throw new Error(`Protected source changed: ${file.path}`);
}
await mkdir(path.join(root,'dist'), {recursive:true});
await cp(path.join(root,'docs'), path.join(root,'dist'), {recursive:true});
const pdfjs=path.join(root,'node_modules','pdfjs-dist'), pdfdest=path.join(root,'dist','vendor','pdfjs');
await mkdir(pdfdest,{recursive:true});
for (const name of ['pdf.mjs','pdf.worker.mjs']) await cp(path.join(pdfjs,'build',name),path.join(pdfdest,name));
for (const name of ['cmaps','standard_fonts','wasm']) await cp(path.join(pdfjs,name),path.join(pdfdest,name),{recursive:true});
await cp(path.join(pdfjs,'web','pdf_viewer.css'),path.join(pdfdest,'pdf_viewer.css'));
await cp(path.join(pdfjs,'LICENSE'),path.join(pdfdest,'LICENSE'));
await cp(path.join(root,'THOMAS-PRIMARY-2025.pdf'),path.join(root,'dist','THOMAS-PRIMARY-2025.pdf'));
for (const name of ['S1_bertopic_optimization.txt','S2_democratic_topic_naming.txt','S3_llm_classification.txt']) await cp(path.join(root,name),path.join(root,'dist',name));
await writeFile(path.join(root,'dist','source-integrity.json'),JSON.stringify(manifest,null,2)+'\n');
const source = await readFile(path.join(root,'THOMAS-PRIMARY-2025.pdf'));
const served = await readFile(path.join(root,'dist','THOMAS-PRIMARY-2025.pdf'));
if (!source.equals(served)) throw new Error('Dissertation copy differs.');
if ((await stat(path.join(root,'dist','index.html'))).size === 0) throw new Error('Missing home page.');
console.log(`Built Cloudflare assets; ${manifest.files.length} protected source files verified byte for byte.`);
