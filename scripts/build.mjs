import {mkdir, cp, readFile, writeFile, stat, rm, readdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const manifest = JSON.parse(await readFile(path.join(root,'source-integrity.json'),'utf8'));
const release = JSON.parse(await readFile(path.join(root,'package.json'),'utf8')).version;
for (const file of manifest.files) {
  const bytes = await readFile(path.join(root,file.path));
  if (createHash('sha256').update(bytes).digest('hex') !== file.sha256) throw new Error(`Protected source changed: ${file.path}`);
}
const dist=path.resolve(root,'dist');
if(path.dirname(dist)!==root||path.basename(dist)!=='dist')throw new Error('Unsafe build target');
await rm(dist,{recursive:true,force:true});
await mkdir(dist, {recursive:true});
// Full source archives include the dissertation and research logs and can
// exceed the host's 25 MiB per-asset limit. The download route uses GitHub.
await cp(path.join(root,'docs'), path.join(root,'dist'), {recursive:true,
  filter:source=>path.basename(source)!=='topicllm-research-source.zip' &&
    (!source.endsWith('.whl') || path.basename(source).startsWith(`topicllm_research-${release}-`))});
// Version the complete browser code/style set, including module imports, so a
// returning visitor cannot combine a new page with a cached earlier interface.
async function siteFiles(dir){
  const files=[];
  for(const entry of await readdir(dir,{withFileTypes:true})){
    const file=path.join(dir,entry.name);
    if(entry.isDirectory())files.push(...await siteFiles(file));else files.push(file);
  }
  return files.sort();
}
const files=await siteFiles(dist), browserHash=createHash('sha256');
for(const file of files)if((await stat(file)).size>25*1024*1024)throw new Error(`Asset exceeds the hosting limit: ${path.relative(dist,file)}`);
for(const file of files.filter(file=>/\.(?:css|js)$/.test(file))){browserHash.update(path.relative(dist,file).replaceAll('\\','/'));browserHash.update(await readFile(file));}
const revision=browserHash.digest('hex').slice(0,12);
for(const file of files.filter(file=>/\.(?:html|js)$/.test(file))){
  let text=await readFile(file,'utf8');
  if(file.endsWith('.html'))text=text.replace(/((?:href|src)=["'])([^"']+\.(?:css|js))(["'])/g,(match,start,url,end)=>/^(?:https?:|\/\/)/.test(url)?match:`${start}${url}?v=${revision}${end}`);
  else text=text.replace(/((?:\bfrom\s*|\bimport\s*)["'])(\.{1,2}\/[^"']+\.js)(["'])/g,`$1$2?v=${revision}$3`);
  await writeFile(file,text);
}
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
