/* site.js — landing-page behavior: theme toggle, copy buttons, citation tabs,
 * download sizes, scroll reveal, and Plate II (published theme prevalence). */

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];

/* ------------------------------------------------------------ theme toggle */
function currentTheme() {
  const set = document.documentElement.dataset.theme;
  if (set) return set;
  return matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}
$$("[data-theme-toggle]").forEach(btn => btn.addEventListener("click", () => {
  const next = currentTheme() === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem("topicllm-theme", next); } catch (e) { /* storage unavailable */ }
  drawPrevalence();
}));

/* ------------------------------------------------------------ copy buttons */
$$(".codeblock").forEach(block => {
  const pre = $("pre", block);
  const btn = document.createElement("button");
  btn.className = "copy"; btn.type = "button"; btn.textContent = "Copy";
  btn.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(pre.innerText);
      btn.textContent = "Copied";
    } catch (e) { btn.textContent = "Select & copy"; }
    setTimeout(() => (btn.textContent = "Copy"), 1600);
  });
  block.appendChild(btn);
});

/* ------------------------------------------------------------- cite tabs */
$$("[data-cite]").forEach(root => {
  const tabs = $$("[data-cite-tab]", root);
  tabs.forEach(tab => tab.addEventListener("click", () => {
    tabs.forEach(t => t.setAttribute("aria-selected", String(t === tab)));
    $$("[data-cite-panel]", root).forEach(p => (p.hidden = p.dataset.citePanel !== tab.dataset.citeTab));
  }));
});

/* ---------------------------------------------------------- download sizes */
const fmt = n => n > 1e6 ? `${(n / 1e6).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1e3))} KB`;
$$("a[data-size]").forEach(async a => {
  try {
    const r = await fetch(a.getAttribute("href"), { method: "HEAD" });
    const n = Number(r.headers.get("content-length"));
    if (!r.ok || !n) return;
    const slot = a.nextElementSibling && a.nextElementSibling.tagName === "SPAN" ? a.nextElementSibling : null;
    if (slot) slot.textContent = fmt(n);
    else a.insertAdjacentHTML("beforeend", ` <span style="opacity:.7;font-weight:400">· ${fmt(n)}</span>`);
  } catch (e) { /* offline or file:// — sizes are optional */ }
});

/* ------------------------------------------------------------------ reveal */
if ("IntersectionObserver" in window) {
  const io = new IntersectionObserver(entries => entries.forEach(e => {
    if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
  }), { rootMargin: "0px 0px -8% 0px" });
  $$(".reveal").forEach(el => io.observe(el));
} else {
  $$(".reveal").forEach(el => el.classList.add("in"));
}

/* ---------------------------------------------------------------- Plate II */
// Published values: Thomas (2025), Study 1, Table 3 (methods preprint Table 2).
const PREVALENCE = [
  { theme: "Alcohol Delivery and Isolation Drinking", v: [9.1, 17.4, 11.9], sig: ["*", "†", "*†"] },
  { theme: "Restaurant Support", v: [1.9, 5.5, 1.7], sig: ["*", "†", "*"] },
  { theme: "Social Media Promotions", v: [6.6, 16.5, 10.6], sig: ["*", "†", "*†"] },
  { theme: "Sports", v: [8.2, 11.4, 8.9], sig: ["", "", ""] },
  { theme: "Gaming", v: [1.1, 2.0, 1.6], sig: ["", "", ""] },
];
const PERIODS = ["Pre-pandemic", "Peri-pandemic", "Post-pandemic"];
const SIG_NOTE = { "*": "differs from peri-pandemic", "†": "differs from pre-pandemic" };
const NS = "http://www.w3.org/2000/svg";

function el(tag, attrs = {}, parent) {
  const node = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (parent) parent.appendChild(node);
  return node;
}

function drawPrevalence() {
  const host = $("#prevalence-viz");
  if (!host) return;
  host.innerHTML = "";
  const width = Math.max(300, host.clientWidth || 900);
  const narrow = width < 640;
  const labelW = narrow ? 0 : 300;
  const rowH = narrow ? 70 : 54;
  const top = 8, bottom = 34, right = 28;
  const height = top + rowH * PREVALENCE.length + bottom;
  const x0 = labelW, x1 = width - right;
  const xMax = 20;
  const x = v => x0 + (v / xMax) * (x1 - x0);

  const svg = el("svg", { viewBox: `0 0 ${width} ${height}`, role: "img",
    "aria-label": "Dot plot of published theme prevalence in pre-, peri- and post-pandemic periods" }, host);

  const grid = el("g", { class: "grid" }, svg);
  const ticks = el("g", { class: "tick" }, svg);
  for (let t = 0; t <= xMax; t += 5) {
    el("line", { x1: x(t), x2: x(t), y1: top, y2: height - bottom + 4 }, grid);
    const tx = el("text", { x: x(t), y: height - 12, "text-anchor": "middle" }, ticks);
    tx.textContent = `${t}%`;
  }

  const css = getComputedStyle(document.documentElement);
  const color = i => css.getPropertyValue(`--series-${i + 1}`).trim();
  const tip = document.createElement("div");
  tip.className = "tooltip"; tip.setAttribute("role", "status");
  host.appendChild(tip);

  PREVALENCE.forEach((row, r) => {
    const cy = top + r * rowH + (narrow ? rowH - 22 : rowH / 2);
    const g = el("g", {}, svg);
    if (narrow) {
      const lab = el("text", { x: x0, y: cy - 20, class: "theme-label" }, g);
      lab.textContent = row.theme;
    } else {
      const lab = el("text", { x: 0, y: cy + 5, class: "theme-label" }, g);
      lab.textContent = row.theme;
    }
    el("line", { class: "span", x1: x(Math.min(...row.v)), x2: x(Math.max(...row.v)), y1: cy, y2: cy }, g);
    // pre: ring; peri: filled circle; post: diamond — identity never color-alone
    el("circle", { cx: x(row.v[0]), cy, r: 6.5, fill: css.getPropertyValue("--surface").trim(),
      stroke: color(0), "stroke-width": 3 }, g);
    const d = 7.5, px = x(row.v[2]);
    el("path", { d: `M${px} ${cy - d} L${px + d} ${cy} L${px} ${cy + d} L${px - d} ${cy} Z`,
      fill: color(2), class: "dot" }, g);
    el("circle", { cx: x(row.v[1]), cy, r: 7.5, fill: color(1), class: "dot" }, g);
    const lbl = el("text", { x: x(row.v[1]) + 13, y: cy + 4.5, class: "sig" }, g);
    lbl.textContent = `${row.v[1].toFixed(1)}%`;

    // generous hit target for the whole row
    const hit = el("rect", { class: "hit", x: 0, y: cy - rowH / 2, width, height: rowH }, g);
    hit.addEventListener("pointerenter", () => show(row, cy));
    hit.addEventListener("pointermove", () => show(row, cy));
    hit.addEventListener("pointerleave", () => tip.classList.remove("on"));
  });

  function show(row, cy) {
    const notes = [...new Set(row.sig.join("").split(""))].map(s => `${s} ${SIG_NOTE[s]}`);
    tip.innerHTML = `<b>${row.theme}</b>` + row.v.map((v, i) =>
      `<div class="row"><span>${PERIODS[i]}</span><span>${v.toFixed(1)}%${row.sig[i] ? " " + row.sig[i] : ""}</span></div>`
    ).join("") + (notes.length ? `<div class="row" style="margin-top:6px"><span>${notes.join("; ")}, p &lt; .0033</span></div>`
                               : `<div class="row" style="margin-top:6px"><span>No significant differences</span></div>`);
    const scale = host.clientWidth / width;
    const left = Math.min(host.clientWidth - 200, Math.max(0, x(Math.max(...row.v)) * scale + 16));
    tip.style.left = `${left}px`;
    tip.style.top = `${Math.max(0, cy * scale - 40)}px`;
    tip.classList.add("on");
  }
}

let resizeTimer;
addEventListener("resize", () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(drawPrevalence, 120); });
matchMedia("(prefers-color-scheme: dark)").addEventListener?.("change", drawPrevalence);
drawPrevalence();
