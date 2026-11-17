/* charts.js — small SVG chart components. Colors come from CSS custom
 * properties (see app.css) so light/dark themes swap in one place; text
 * wears ink tokens, never series colors; grid is recessive hairline. */

import { escapeHTML } from "./util.js";

const NS = "http://www.w3.org/2000/svg";

function el(tag, attrs = {}, parent = null) {
  const node = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (parent) parent.appendChild(node);
  return node;
}

let tooltipDiv = null;
function tooltip() {
  if (!tooltipDiv) {
    tooltipDiv = document.createElement("div");
    tooltipDiv.className = "chart-tooltip";
    tooltipDiv.style.display = "none";
    document.body.appendChild(tooltipDiv);
  }
  return tooltipDiv;
}
function showTip(evt, html) {
  const t = tooltip();
  t.innerHTML = html;
  t.style.display = "block";
  const pad = 12;
  let x = evt.clientX + pad, y = evt.clientY + pad;
  const r = t.getBoundingClientRect();
  if (x + r.width > innerWidth - 8) x = evt.clientX - r.width - pad;
  if (y + r.height > innerHeight - 8) y = evt.clientY - r.height - pad;
  t.style.left = x + "px"; t.style.top = y + "px";
}
function hideTip() { if (tooltipDiv) tooltipDiv.style.display = "none"; }

/** Path for a bar rounded only at its data end (top for vertical bars,
 * right for horizontal), square at the baseline. */
function barPath(x, y, w, h, r, horizontal = false) {
  r = Math.min(r, w / 2, h / 2);
  if (horizontal) {
    return `M${x},${y} h${w - r} a${r},${r} 0 0 1 ${r},${r} v${h - 2 * r} a${r},${r} 0 0 1 -${r},${r} h-${w - r} z`;
  }
  return `M${x},${y + h} v-${h - r} a${r},${r} 0 0 1 ${r},-${r} h${w - 2 * r} a${r},${r} 0 0 1 ${r},${r} v${h - r} z`;
}

function niceTicks(min, max, count = 5) {
  if (min === max) { max = min + 1; }
  const span = max - min;
  const step0 = span / count;
  const mag = Math.pow(10, Math.floor(Math.log10(step0)));
  const step = [1, 2, 2.5, 5, 10].map(m => m * mag).find(s => span / s <= count) || mag * 10;
  const lo = Math.floor(min / step) * step;
  const ticks = [];
  for (let v = lo; v <= max + step * 0.001; v += step) if (v >= min - step * 0.001) ticks.push(+v.toFixed(10));
  return ticks;
}

/** Coherence-curve style line chart: single series, crosshair + tooltip,
 * the selected/highlighted point direct-labeled. */
export function lineChart(container, { points, xLabel, yLabel, highlightX, valueFmt = v => v.toFixed(4) }) {
  container.innerHTML = "";
  const W = Math.max(container.clientWidth || 560, 320), H = 260;
  const m = { top: 16, right: 20, bottom: 44, left: 56 };
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, class: "chart", role: "img" }, container);

  const xs = points.map(p => p[0]), ys = points.map(p => p[1]);
  const xMin = Math.min(...xs), xMax = Math.max(...xs);
  const yMin = Math.min(...ys), yMax = Math.max(...ys);
  const yPad = (yMax - yMin || 0.1) * 0.12;
  const X = v => m.left + (v - xMin) / (xMax - xMin || 1) * (W - m.left - m.right);
  const Y = v => H - m.bottom - (v - (yMin - yPad)) / ((yMax + yPad) - (yMin - yPad)) * (H - m.top - m.bottom);

  for (const t of niceTicks(yMin - yPad, yMax + yPad, 4)) {
    el("line", { x1: m.left, x2: W - m.right, y1: Y(t), y2: Y(t), class: "grid" }, svg);
    el("text", { x: m.left - 8, y: Y(t) + 4, class: "tick", "text-anchor": "end" }, svg).textContent = t.toFixed(yMax-yMin<0.05?4:2);
  }
  for (const t of niceTicks(xMin, xMax, 8).filter(Number.isInteger)) {
    el("text", { x: X(t), y: H - m.bottom + 18, class: "tick", "text-anchor": "middle" }, svg).textContent = t;
  }
  el("line", { x1: m.left, x2: W - m.right, y1: H - m.bottom, y2: H - m.bottom, class: "axis" }, svg);
  el("text", { x: (m.left + W - m.right) / 2, y: H - 8, class: "axis-label", "text-anchor": "middle" }, svg).textContent = xLabel;
  el("text", { x: 14, y: (m.top + H - m.bottom) / 2, class: "axis-label", "text-anchor": "middle",
    transform: `rotate(-90 14 ${(m.top + H - m.bottom) / 2})` }, svg).textContent = yLabel;

  const sorted = [...points].sort((a, b) => a[0] - b[0]);
  el("path", {
    d: sorted.map((p, i) => `${i ? "L" : "M"}${X(p[0]).toFixed(1)},${Y(p[1]).toFixed(1)}`).join(""),
    class: "series-line", fill: "none",
  }, svg);

  for (const [x, y] of sorted) {
    const isHi = x === highlightX;
    el("circle", { cx: X(x), cy: Y(y), r: isHi ? 5 : 3, class: isHi ? "dot dot-hi" : "dot" }, svg);
    if (isHi) {
      const nearLeft=X(x)<m.left+90, nearRight=X(x)>W-m.right-90;
      el("text", { x: X(x)+(nearLeft?12:nearRight?-12:0), y: Y(y) - 14, class: "direct-label", "text-anchor": nearLeft?"start":nearRight?"end":"middle" }, svg)
        .textContent = `${valueFmt(y)} @ ${x}`;
    }
    const hit = el("circle", { cx: X(x), cy: Y(y), r: 12, fill: "transparent" }, svg);
    hit.addEventListener("pointermove", evt =>
      showTip(evt, `<strong>${escapeHTML(String(xLabel))}: ${x}</strong><br>${escapeHTML(yLabel)}: ${valueFmt(y)}`));
    hit.addEventListener("pointerleave", hideTip);
  }
}

/** Horizontal single-series bars (e.g. modal vote share per topic). */
export function hBarChart(container, { items, valueFmt = v => v, maxValue }) {
  container.innerHTML = "";
  const W = Math.max(container.clientWidth || 560, 320);
  const rowH = 30, labelW = Math.min(240, W * 0.4);
  const H = items.length * rowH + 8;
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, class: "chart", role: "img" }, container);
  const vMax = maxValue ?? Math.max(...items.map(i => i.value), 0.0001);
  for (let i = 0; i < items.length; i++) {
    const { label, value, detail } = items[i];
    const y = i * rowH + 5, barH = rowH - 12;
    const bw = Math.max((value / vMax) * (W - labelW - 90), 2);
    el("text", { x: labelW - 8, y: y + barH / 2 + 4, class: "tick", "text-anchor": "end" }, svg)
      .textContent = label.length > 34 ? label.slice(0, 33) + "…" : label;
    const bar = el("path", { d: barPath(labelW, y, bw, barH, 4, true), class: "bar s1" }, svg);
    el("text", { x: labelW + bw + 8, y: y + barH / 2 + 4, class: "direct-label" }, svg).textContent = valueFmt(value);
    bar.addEventListener("pointermove", evt =>
      showTip(evt, `<strong>${escapeHTML(label)}</strong><br>${escapeHTML(detail || valueFmt(value))}`));
    bar.addEventListener("pointerleave", hideTip);
  }
}

/** Prevalence by theme: direct labels and full names at every viewport width. */
export function groupedBarChart(container, { groups, series, values, valueFmt = v => Number(v.toFixed(1)) + "%" }) {
  container.innerHTML='';
  const W=Math.max(container.clientWidth||640,260),narrow=W<620;
  const left=narrow?36:Math.min(265,W*.35),right=48;
  const max=Math.max(...values.flat(),.001),limit=Math.ceil(max/5)*5;
  const plot=W-left-right,X=value=>left+value/limit*plot;
  const names={pre:'Pre',peri:'Peri',post:'Post'};
  const svg=el('svg',{class:'chart',role:'img','aria-label':'Theme prevalence by period. Read the accompanying table and source description for values and provenance.'},container);
  let y=28;
  if(!narrow){let lx=left;series.forEach((period,i)=>{el('rect',{x:lx,y:2,width:8,height:8,rx:2,class:`bar s${i+1}`},svg);el('text',{x:lx+14,y:10,class:'tick'},svg).textContent=names[period]||period;lx+=80;});}
  for(let t=0;t<=limit;t+=5){el('text',{x:X(t),y:y+7,class:'tick','text-anchor':'middle'},svg).textContent=t+'%';}
  y+=24;
  groups.forEach((group,gi)=>{
    const lineWidth=narrow?Math.max(20,Math.floor(W/6.5)):Math.floor((left-28)/6.5),lines=[''];
    for(const word of group.split(' ')){const i=lines.length-1;if(lines[i]&&(lines[i]+' '+word).length>lineWidth)lines.push(word);else lines[i]+=(lines[i]?' ':'')+word;}
    if(narrow){for(const line of lines){el('text',{x:0,y:y+9,class:'theme-label'},svg).textContent=line;y+=15;}y+=7;}
    else lines.forEach((line,i)=>{el('text',{x:0,y:y+16+i*15,class:'theme-label'},svg).textContent=line;});
    for(let t=0;t<=limit;t+=5)el('line',{x1:X(t),x2:X(t),y1:y-2,y2:y+series.length*17-1,class:'grid'},svg);
    series.forEach((period,si)=>{
      const value=values[gi][si],yy=y+si*17;
      if(narrow)el('text',{x:0,y:yy+9,class:'tick'},svg).textContent=names[period]||period;
      const bar=el('rect',{x:left,y:yy,width:Math.max(0,X(value)-left),height:10,rx:2,class:`bar s${si+1}`,tabindex:'0',role:'img','aria-label':`${group}, ${names[period]||period}: ${valueFmt(value)}`},svg);
      el('text',{x:X(value)+7,y:yy+9,class:'tick'},svg).textContent=valueFmt(value);
      bar.addEventListener('pointermove',evt=>showTip(evt,`<strong>${escapeHTML(group)}</strong><br>${escapeHTML(names[period]||period)}: ${valueFmt(value)}`));bar.addEventListener('pointerleave',hideTip);
    });
    y+=series.length*17+27;
  });
  svg.setAttribute('viewBox',`0 0 ${W} ${y-8}`);
}
