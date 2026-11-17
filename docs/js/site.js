/* site.js — landing-page behavior: theme toggle, copy buttons, citation tabs,
 * download sizes, scroll reveal, and scroll reveals. */

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
