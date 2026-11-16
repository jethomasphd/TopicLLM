/* Render the unchanged dissertation bytes, with selectable original text. */
import {getDocument, GlobalWorkerOptions, TextLayer} from '../vendor/pdfjs/pdf.mjs';
GlobalWorkerOptions.workerSrc = new URL('../vendor/pdfjs/pdf.worker.mjs',import.meta.url).href;
const root=document.querySelector('[data-source-reader]');
const first=Number(root.dataset.first), last=Number(root.dataset.last);
const input=document.getElementById('source-page'), status=document.getElementById('source-status');
const previous=document.getElementById('source-prev'), next=document.getElementById('source-next');
const zoom=document.getElementById('source-zoom'), host=document.getElementById('source-scroll');
const go=document.getElementById('source-go');
let pdf, rendering=false, wanted=Number(new URLSearchParams(location.hash.slice(1)).get('page'))||first;
wanted=Math.max(first,Math.min(last,wanted));
input.min=first;input.max=last;input.value=wanted;

async function render() {
  if (!pdf || rendering) return;
  rendering=true;previous.disabled=next.disabled=true;input.disabled=zoom.disabled=go.disabled=true;
  const number=wanted;
  try {
    status.textContent=`Rendering original page ${number}…`;
    const page=await pdf.getPage(number), native=page.getViewport({scale:1});
    const scale=Math.min(host.clientWidth-4,900)/native.width*Number(zoom.value);
    const viewport=page.getViewport({scale}), ratio=Math.min(devicePixelRatio||1,2);
    const surface=document.createElement('div');surface.className='source-page';
    surface.style.width=`${viewport.width}px`;surface.style.height=`${viewport.height}px`;
    surface.style.setProperty('--total-scale-factor',scale);
    const canvas=document.createElement('canvas');canvas.setAttribute('aria-hidden','true');
    canvas.width=Math.ceil(viewport.width*ratio);canvas.height=Math.ceil(viewport.height*ratio);
    canvas.style.width=`${viewport.width}px`;canvas.style.height=`${viewport.height}px`;
    const text=document.createElement('div');text.className='textLayer';
    surface.append(canvas,text);host.replaceChildren(surface);
    await page.render({canvasContext:canvas.getContext('2d'),viewport,transform:[ratio,0,0,ratio,0,0]}).promise;
    await new TextLayer({textContentSource:page.streamTextContent(),container:text,viewport}).render();
    input.value=number;history.replaceState(null,'',`#page=${number}`);
    status.textContent=`Source checksum verified · original page ${number} of ${pdf.numPages} · chapter pages ${first}–${last}`;
  } catch(error) {
    status.textContent='The page could not be rendered. Use “Download unchanged dissertation” above.';
    console.error('Source reader render failed',error);
  } finally {
    rendering=false;input.disabled=zoom.disabled=go.disabled=false;
    previous.disabled=number<=first;next.disabled=number>=last;
    if(wanted!==number)render();
  }
}
previous.onclick=()=>{wanted=Math.max(first,wanted-1);render();};
next.onclick=()=>{wanted=Math.min(last,wanted+1);render();};
input.onchange=()=>{wanted=Math.max(first,Math.min(last,Number(input.value)||first));render();};
go.onclick=input.onchange;
input.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();input.onchange();}};
zoom.onchange=render;
let resizeTimer;
addEventListener('resize',()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(render,200);});
try {
  const [response,manifestResponse]=await Promise.all([fetch('../../THOMAS-PRIMARY-2025.pdf'),fetch('../../source-integrity.json')]);
  if(!response.ok||!manifestResponse.ok)throw new Error('Source unavailable');
  const bytes=new Uint8Array(await response.arrayBuffer()), manifest=await manifestResponse.json();
  const hash=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(v=>v.toString(16).padStart(2,'0')).join('');
  if(hash!==manifest.files.find(f=>f.path==='THOMAS-PRIMARY-2025.pdf')?.sha256)throw new Error('Source checksum mismatch');
  pdf=await getDocument({data:bytes,isEvalSupported:false,cMapUrl:'../../vendor/pdfjs/cmaps/',cMapPacked:true,standardFontDataUrl:'../../vendor/pdfjs/standard_fonts/',wasmUrl:'../../vendor/pdfjs/wasm/'}).promise;
  await render();
} catch(error) {status.textContent=`Unable to load the verified source: ${error.message}. The original download remains available.`;}
