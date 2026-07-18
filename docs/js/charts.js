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
    el("text", { x: m.left - 8, y: Y(t) + 4, class: "tick", "text-anchor": "end" }, svg).textContent = t.toFixed(2);
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
      el("text", { x: X(x), y: Y(y) - 10, class: "direct-label", "text-anchor": "middle" }, svg)
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

/** Grouped vertical bars: themes × periods (≤4 series, legend + gaps). */
export function groupedBarChart(container, { groups, series, values, valueFmt = v => v + "%" }) {
  container.innerHTML = "";
  const W = Math.max(container.clientWidth || 640, 360), H = 300;
  const m = { top: 34, right: 12, bottom: 74, left: 46 };
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, class: "chart", role: "img" }, container);

  const vMax = Math.max(...values.flat(), 0.001) * 1.15;
  const Y = v => H - m.bottom - (v / vMax) * (H - m.top - m.bottom);
  for (const t of niceTicks(0, vMax, 4)) {
    el("line", { x1: m.left, x2: W - m.right, y1: Y(t), y2: Y(t), class: "grid" }, svg);
    el("text", { x: m.left - 8, y: Y(t) + 4, class: "tick", "text-anchor": "end" }, svg).textContent = valueFmt(t);
  }
  el("line", { x1: m.left, x2: W - m.right, y1: H - m.bottom, y2: H - m.bottom, class: "axis" }, svg);

  const groupW = (W - m.left - m.right) / groups.length;
  const barGap = 2, barW = Math.min(26, (groupW - 16) / series.length - barGap);
  groups.forEach((g, gi) => {
    const x0 = m.left + gi * groupW + (groupW - series.length * (barW + barGap)) / 2;
    series.forEach((s, si) => {
      const v = values[gi][si];
      if (v == null) return;
      const x = x0 + si * (barW + barGap), y = Y(v);
      const bar = el("path", { d: barPath(x, y, barW, H - m.bottom - y, 4), class: `bar s${si + 1}` }, svg);
      bar.addEventListener("pointermove", evt =>
        showTip(evt, `<strong>${escapeHTML(g)}</strong><br>${escapeHTML(s)}: ${valueFmt(v)}`));
      bar.addEventListener("pointerleave", hideTip);
    });
    const words = g.split(" ");
    const lines = words.length > 2 ? [words.slice(0, Math.ceil(words.length / 2)).join(" "),
      words.slice(Math.ceil(words.length / 2)).join(" ")] : [g];
    lines.forEach((ln, li) => {
      el("text", { x: m.left + gi * groupW + groupW / 2, y: H - m.bottom + 16 + li * 13,
        class: "tick", "text-anchor": "middle" }, svg)
        .textContent = ln.length > 20 ? ln.slice(0, 19) + "…" : ln;
    });
  });

  // legend (>= 2 series): colored chip + ink text
  let lx = m.left;
  series.forEach((s, si) => {
    el("rect", { x: lx, y: 8, width: 12, height: 12, rx: 3, class: `bar s${si + 1}` }, svg);
    const t = el("text", { x: lx + 17, y: 18, class: "tick" }, svg);
    t.textContent = s;
    lx += 17 + s.length * 6.6 + 22;
  });
}
