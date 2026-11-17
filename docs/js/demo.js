/* Original Study 1 discovery input; no synthetic labels are attached. */
import {parseCSV} from './util.js';
import {sha256} from './research.js';
export const NONE_LABEL='The text does not fit into any of these themes';
export async function loadDemoData(){
 const base=new URL('../data/study1/',import.meta.url);
 const get=async name=>{const r=await fetch(new URL(name,base));if(!r.ok)throw new Error(`Could not load ${name}`);return r.text();};
 const [raw,stop,manifest]=await Promise.all([get('discovery.csv'),get('stopwords.txt'),get('manifest.json')]);
 if(await sha256(raw)!==JSON.parse(manifest).files['discovery.csv'].sha256)throw new Error('Study 1 input checksum mismatch.');
 return {corpus:parseCSV(raw).rows,benchmark:null,stopwords:stop.trim()};
}
