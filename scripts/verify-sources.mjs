import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const root=new URL('../',import.meta.url);
const manifest=JSON.parse(await readFile(new URL('source-integrity.json',root),'utf8'));
for(const source of manifest.files){const bytes=await readFile(new URL(source.path,root));if(createHash('sha256').update(bytes).digest('hex')!==source.sha256)throw new Error(`Protected source changed: ${source.path}`);}
console.log(`Verified ${manifest.files.length} protected source files byte for byte.`);
