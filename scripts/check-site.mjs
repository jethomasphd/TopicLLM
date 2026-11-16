import {readdir,readFile,stat} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const root=path.resolve(fileURLToPath(new URL('../dist/',import.meta.url)));
async function walk(dir){const out=[];for(const e of await readdir(dir,{withFileTypes:true})){const p=path.join(dir,e.name);if(e.isDirectory())out.push(...await walk(p));else if(e.name.endsWith('.html'))out.push(p);}return out;}
let checked=0;
for(const file of await walk(root)){
  const html=await readFile(file,'utf8');
  for(const [,href] of html.matchAll(/(?:href|src)=["']([^"']+)["']/g)){
    if(/^(?:https?:|mailto:|tel:|data:|#|\/\/)/.test(href))continue;
    const pathname=decodeURIComponent(href.split(/[?#]/)[0]);if(!pathname)continue;
    let target=pathname.startsWith('/')?path.join(root,pathname):path.resolve(path.dirname(file),pathname);
    if(target!==root&&!target.startsWith(root+path.sep))throw new Error(`Link leaves site: ${href}`);
    let info;try{info=await stat(target);}catch{throw new Error(`Broken local link in ${path.relative(root,file)}: ${href}`);}
    if(info.isDirectory()){target=path.join(target,'index.html');await stat(target);}
    checked++;
  }
}
console.log(`Verified ${checked} local links and asset references in the built HTML.`);
