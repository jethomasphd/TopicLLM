/* app.js — UI orchestration for the browser pipeline.
 * Stage 1 runs in a Web Worker; Stages 2–5 run here (LLM calls are async
 * network requests to the endpoint the user configures; statistics are
 * computed locally). Every stage exposes the same artifacts the Python
 * reference implementation writes to disk, as downloads. */

import { parseCSV, toCSV, downloadText, downloadBlob, buildZip, mulberry32, sample, slug, pct, escapeHTML } from "./util.js";
import { createProvider, callWithRetries, pool } from "./llm.js";
import { makeDemoData, NONE_LABEL } from "./demo.js";
import { proportionsZTest } from "./stats.js";
import { lineChart, hBarChart, groupedBarChart } from "./charts.js";

/* ------------------------------ state ------------------------------------ */

const S = {
  corpus: null,          // [{tweet, date?, ...}]
  textCol: "tweet",
  benchmark: null,       // [{tweet, human_label}]
  stage1: null,          // worker payload
  stage2: null,          // { winners, ballots }
  stage3: null,          // { themeMap: [{topic, modal_label, theme}], themes }
  stage4: null,          // { report, benchRows, classified }
  stage5: null,          // { prevRows, testRows, alphaAdj }
  isDemo: false,
};

const DEFAULT_STOPWORDS = "budlight,budweiser,truly,malibu,jagermeister,samueladams,brooklynbrewery,jackdaniels,bacardi,absolut,whiteclaw,am,pm,monday,tuesday,wednesday,thursday,friday,saturday,sunday,january,february,march,april,may,june,july,august,september,october,november,december";

const $ = id => document.getElementById(id);
const on = (id, evt, fn) => $(id).addEventListener(evt, fn);

function log(boxId, text, level = "info") {
  const box = $(boxId);
  const line = document.createElement("div");
  line.className = "log-line " + level;
  line.textContent = text;
  box.appendChild(line);
  box.scrollTop = box.scrollHeight;
}

function setStageState(n, state, note = "") {
  const badge = $(`badge-${n}`);
  badge.className = "badge " + state;
  badge.textContent = { idle: "not run", running: "running…", done: "complete", blocked: "blocked", error: "error" }[state] || state;
  if (note) badge.title = note;
}

/* --------------------------- data loading -------------------------------- */

function summarizeData() {
  const el = $("data-summary");
  if (!S.corpus) { el.innerHTML = "<em>No corpus loaded.</em>"; return; }
  const hasDate = S.corpus.some(r => r.date);
  el.innerHTML =
    `<strong>${S.corpus.length.toLocaleString()}</strong> documents loaded` +
    `${S.isDemo ? " (synthetic demo)" : ""} — text column <code>${escapeHTML(S.textCol)}</code>` +
    `${hasDate ? ", with dates" : ", no date column (Stage 5 period tests disabled)"}.` +
    (S.benchmark ? ` Benchmark: <strong>${S.benchmark.length}</strong> human-labeled documents.`
                 : " No benchmark loaded (needed for Stage 4).");
  $("run1").disabled = !S.corpus;
}

function loadDemo() {
  const { corpus, benchmark } = makeDemoData(7);
  S.corpus = corpus; S.benchmark = benchmark; S.textCol = "tweet"; S.isDemo = true;
  $("stopwords").value = "";  // demo corpus has no brand terms
  summarizeData();
  log("log-1", "Demo corpus generated: 600 synthetic documents, 250-document benchmark.");
}

async function readFileText(file) { return await file.text(); }

async function loadCorpusFile(file) {
  const { header, rows } = parseCSV(await readFileText(file));
  if (!rows.length) { alert("No rows found in the CSV."); return; }
  const textCol = header.includes("tweet") ? "tweet"
    : header.includes("text") ? "text" : header[0];
  S.corpus = rows; S.textCol = textCol; S.isDemo = false;
  summarizeData();
}

async function loadBenchmarkFile(file) {
  const { header, rows } = parseCSV(await readFileText(file));
  if (!(header.includes("tweet") && header.includes("human_label"))) {
    alert("Benchmark CSV needs columns: tweet, human_label"); return;
  }
  S.benchmark = rows;
  summarizeData();
}

/* ------------------------- provider settings ----------------------------- */

function providerSettings() {
  return {
    provider: $("llm-provider").value,
    apiKey: $("llm-key").value.trim(),
    baseUrl: $("llm-base").value.trim(),
    model: $("llm-model").value.trim(),
  };
}

function makeProvider(mockHints) {
  const s = providerSettings();
  if (s.provider !== "mock" && !s.apiKey) {
    throw new Error("Enter an API key, or switch the provider to the keyless demo mock.");
  }
  return createProvider({ ...s, mockHints });
}

function persistSettings() {
  const s = providerSettings();
  const store = { provider: s.provider, baseUrl: s.baseUrl, model: s.model };
  if ($("llm-remember").checked) store.apiKey = s.apiKey;
  localStorage.setItem("topicllm-settings", JSON.stringify(store));
}

function restoreSettings() {
  try {
    const s = JSON.parse(localStorage.getItem("topicllm-settings") || "{}");
    if (s.provider) $("llm-provider").value = s.provider;
    if (s.baseUrl) $("llm-base").value = s.baseUrl;
    if (s.model) $("llm-model").value = s.model;
    if (s.apiKey) { $("llm-key").value = s.apiKey; $("llm-remember").checked = true; }
  } catch { /* ignore */ }
  syncProviderUI();
}

function syncProviderUI() {
  const p = $("llm-provider").value;
  $("llm-key").disabled = p === "mock";
  $("llm-base").disabled = p !== "openai";
  if (p === "openai" && !$("llm-model").value) $("llm-model").value = "gpt-4o";
  if (p === "anthropic" && (!$("llm-model").value || $("llm-model").value === "gpt-4o")) {
    $("llm-model").value = "claude-haiku-4-5-20251001";
  }
}

/* ------------------------------ stage 1 ---------------------------------- */

let worker = null;

function stage1Config() {
  return {
    randomSeed: parseInt($("cfg-seed").value, 10) || 42,
    searchIterations: parseInt($("cfg-iters").value, 10) || 10,
    topicMin: 2,
    topicMax: parseInt($("cfg-topicmax").value, 10) || 25,
    embedder: $("cfg-embedder").value,
    umapSpace: {
      n_neighbors: [5, 10, 15, 20, 25, 30, 35],
      n_components: [3, 4, 5, 6, 7, 8, 9, 10],
      min_dist: [0.01, 0.05, 0.1, 0.5],
    },
    hdbscanSpace: { min_cluster_size: [5, 10, 15, 20, 25, 30, 35] },
  };
}

function runStage1() {
  if (!S.corpus) return;
  $("run1").disabled = true; $("cancel1").disabled = false;
  $("log-1").innerHTML = ""; $("stage1-results").hidden = true;
  setStageState(1, "running");
  let modelCount = 0;

  worker = new Worker(new URL("./worker1.js", import.meta.url), { type: "module" });
  worker.onmessage = (e) => {
    const msg = e.data;
    if (msg.type === "status") log("log-1", msg.text, msg.level || "info");
    else if (msg.type === "iteration") {
      log("log-1", `Iteration ${msg.iteration}/${msg.total} — UMAP ${JSON.stringify(msg.umapParams)} · HDBSCAN ${JSON.stringify(msg.hdbParams)}`);
    } else if (msg.type === "model") {
      modelCount++;
      if (modelCount % 5 === 0) $("s1-count").textContent = `${modelCount} candidate models scored`;
    } else if (msg.type === "best") {
      log("log-1", `** New best: coherence ${msg.coherence.toFixed(4)} at ${msg.nTopics} topics (iteration ${msg.iteration}) **`, "best");
    } else if (msg.type === "error") {
      log("log-1", msg.message, "warn"); setStageState(1, "error");
      $("run1").disabled = false; $("cancel1").disabled = true;
    } else if (msg.type === "done") {
      S.stage1 = msg.payload;
      S.stage2 = S.stage3 = S.stage4 = S.stage5 = null;
      renderStage1();
      setStageState(1, "done");
      $("run1").disabled = false; $("cancel1").disabled = true;
      $("run2").disabled = false;
      worker.terminate(); worker = null;
    }
  };
  worker.postMessage({
    rows: S.corpus, textCol: S.textCol,
    customStopwords: $("stopwords").value,
    config: stage1Config(),
  });
}

function cancelStage1() {
  if (worker) { worker.terminate(); worker = null; }
  setStageState(1, "idle");
  log("log-1", "Stage 1 cancelled.", "warn");
  $("run1").disabled = false; $("cancel1").disabled = true;
}

function renderStage1() {
  const p = S.stage1;
  $("stage1-results").hidden = false;
  $("s1-count").textContent = "";
  const b = p.best;
  $("s1-summary").innerHTML =
    `Best configuration — iteration ${b.iteration}: <strong>${b.nTopics} topics</strong>, ` +
    `c<sub>v</sub> coherence <strong>${b.coherence.toFixed(4)}</strong> ` +
    `(UMAP: ${b.umapParams.n_neighbors} neighbors, ${b.umapParams.n_components} components, ` +
    `min_dist ${b.umapParams.min_dist}; HDBSCAN: min cluster ${b.hdbParams.min_cluster_size}). ` +
    `Embedder: ${p.embedderUsed === "minilm" ? "all-MiniLM-L6-v2" : "hashed fallback (demo quality)"} · ` +
    `${(p.elapsedMs / 1000).toFixed(1)}s.`;
  lineChart($("s1-chart"), {
    points: p.coherenceCurve, xLabel: "Number of Topics",
    yLabel: "Coherence (c_v)", highlightX: b.nTopics,
  });
  const rows = b.topics.map(t => `<tr><td>${t.id}</td><td>${t.size}</td><td>${escapeHTML(t.words.join(", "))}</td></tr>`).join("");
  $("s1-topics").innerHTML =
    `<table><thead><tr><th>Topic</th><th>Docs</th><th>Representative words (c-TF-IDF)</th></tr></thead><tbody>${rows}</tbody></table>`;
}

function stage1Downloads(which) {
  const p = S.stage1;
  if (!p) return;
  if (which === "audit") {
    downloadText("all_iteration_results.json",
      JSON.stringify({ seed: stage1Config().randomSeed, embedder: p.embedderUsed, iterations: p.allIterations }, null, 2), "application/json");
  } else if (which === "topics") {
    downloadText("topics_for_naming.csv", toCSV(p.topicsForNaming, ["topic", "words"]), "text/csv");
  } else if (which === "pre") {
    const rows = p.keptRows.map((r, i) => ({ [S.textCol]: r[S.textCol], date: r.date || "", preprocessed: r.preprocessed, topic: p.best.labels[i] }));
    downloadText("classified_tweets.csv", toCSV(rows), "text/csv");
  } else if (which === "params") {
    downloadText("parameters.json", JSON.stringify({
      umap_params: p.best.umapParams, hdbscan_params: p.best.hdbParams,
      n_topics: p.best.nTopics, coherence: p.best.coherence,
      seed: stage1Config().randomSeed, embedder: p.embedderUsed,
    }, null, 2), "application/json");
  }
}

/* ------------------------------ stage 2 ---------------------------------- */

const normalizeLabel = s => s.trim().replace(/\.+$/, "").toLowerCase();

async function runStage2() {
  if (!S.stage1) return;
  const votesPerTopic = parseInt($("cfg-votes").value, 10) || 100;
  const earlyStop = $("cfg-earlystop").checked;
  const earlyWindow = parseInt($("cfg-earlywindow").value, 10) || 50;
  const earlyShare = parseFloat($("cfg-earlyshare").value) || 0.6;
  const concurrency = parseInt($("cfg-concurrency").value, 10) || 6;
  const domain = $("cfg-domain").value.trim() || "the corpus under analysis";

  let provider;
  try { provider = makeProvider(null); } catch (err) { alert(err.message); return; }
  persistSettings();

  $("run2").disabled = true; setStageState(2, "running");
  $("log-2").innerHTML = ""; $("stage2-results").hidden = true;
  log("log-2", `Model: ${provider.label} · up to ${votesPerTopic} votes/topic · early stop ${earlyStop ? "on" : "off"}`);
  log("log-2", `Reference implementation uses 5,000 votes/topic; tune for cost as the paper discusses.`);

  const ballots = [], winners = [];
  for (const t of S.stage1.topicsForNaming) {
    const counts = new Map(), display = new Map();
    let issued = 0, completed = 0, stopped = false;
    log("log-2", `Topic ${t.topic}: [${t.words}]`);
    const prompt =
      `The following words represent a topic derived from ${domain}: ${t.words}. ` +
      `Please provide a concise, meaningful topic name that clearly summarizes these words. `;

    while (issued < votesPerTopic && !stopped) {
      const batch = Math.min(concurrency, votesPerTopic - issued);
      const base = issued;
      const tasks = Array.from({ length: batch }, (_, k) => async () => {
        const label = await callWithRetries(
          () => provider.chat("You are an expert at naming topics.", prompt, { temperature: 0.5, maxTokens: 15 }),
          5, (err, n, wait) => log("log-2", `API error (${String(err).slice(0, 80)}); retry ${n}/5 in ${wait / 1000}s`, "warn"));
        return { vote_index: base + k + 1, label };
      });
      issued += batch;
      const results = await pool(tasks, concurrency);
      for (const r of results) {
        completed++;
        const key = normalizeLabel(r.label);
        if (!display.has(key)) display.set(key, r.label);
        counts.set(key, (counts.get(key) || 0) + 1);
        ballots.push({ topic: t.topic, vote_index: r.vote_index, label: r.label });
      }
      const [leadKey, leadN] = [...counts.entries()].sort((a, b) => b[1] - a[1])[0];
      $("s2-live").textContent = `Topic ${t.topic}: ${completed}/${votesPerTopic} votes — leader: “${display.get(leadKey)}” (${pct(leadN / completed)})`;
      if (earlyStop && completed >= earlyWindow && leadN / completed >= earlyShare) {
        log("log-2", `Early stop at ${completed} votes (leader share ${pct(leadN / completed)} ≥ ${pct(earlyShare, 0)})`);
        stopped = true;
      }
    }
    const total = [...counts.values()].reduce((s, x) => s + x, 0);
    const sorted = [...counts.entries()].sort((a, b) => b[1] - a[1]);
    const [winKey, winN] = sorted[0];
    const margin = sorted.length > 1 ? (winN - sorted[1][1]) / total : 1;
    winners.push({
      topic: t.topic, words: t.words, modal_label: display.get(winKey),
      votes_for_modal: winN, total_votes: total,
      modal_share: +(winN / total).toFixed(4),
      margin_over_runner_up: +margin.toFixed(4),
    });
    log("log-2", `WINNER — topic ${t.topic}: “${display.get(winKey)}” (${winN}/${total} = ${pct(winN / total)})`, "best");
  }

  S.stage2 = { ballots, winners, model: provider.model };
  S.stage3 = S.stage4 = S.stage5 = null;
  renderStage2();
  setStageState(2, "done");
  $("run2").disabled = false;
  $("s2-live").textContent = "";
  buildStage3();
}

function renderStage2() {
  $("stage2-results").hidden = false;
  hBarChart($("s2-chart"), {
    items: S.stage2.winners.map(w => ({
      label: `T${w.topic} · ${w.modal_label}`,
      value: w.modal_share,
      detail: `${w.votes_for_modal}/${w.total_votes} votes · margin over runner-up ${pct(w.margin_over_runner_up)}`,
    })),
    valueFmt: v => pct(v), maxValue: 1,
  });
  const rows = S.stage2.winners.map(w =>
    `<tr><td>${w.topic}</td><td>${escapeHTML(w.modal_label)}</td><td>${pct(w.modal_share)}</td>` +
    `<td>${pct(w.margin_over_runner_up)}</td><td>${w.total_votes}</td></tr>`).join("");
  $("s2-table").innerHTML =
    `<table><thead><tr><th>Topic</th><th>Modal label</th><th>Vote share</th><th>Margin</th><th>Votes</th></tr></thead><tbody>${rows}</tbody></table>` +
    `<p class="note">A fragmented vote (low modal share) flags a semantically ambiguous topic — give it extra scrutiny in Stage 3.</p>`;
}

function stage2Downloads(which) {
  if (!S.stage2) return;
  if (which === "log") downloadText("vote_log.csv", toCSV(S.stage2.ballots, ["topic", "vote_index", "label"]), "text/csv");
  else if (which === "tallies") {
    const tally = new Map();
    for (const b of S.stage2.ballots) {
      const key = `${b.topic}\u0000${normalizeLabel(b.label)}`;
      tally.set(key, (tally.get(key) || 0) + 1);
    }
    const rows = [...tally.entries()].map(([k, votes]) => {
      const [topic, norm] = k.split("\u0000");
      return { topic: +topic, norm, votes };
    }).sort((a, b) => a.topic - b.topic || b.votes - a.votes);
    downloadText("vote_tallies.csv", toCSV(rows, ["topic", "norm", "votes"]), "text/csv");
  } else if (which === "names") {
    downloadText("topic_names.csv", toCSV(S.stage2.winners,
      ["topic", "words", "modal_label", "votes_for_modal", "total_votes", "modal_share", "margin_over_runner_up"]), "text/csv");
  }
}

/* ------------------------------ stage 3 ---------------------------------- */

function buildStage3() {
  const box = $("s3-worksheet");
  box.innerHTML = "";
  const rng = mulberry32(parseInt($("cfg-seed").value, 10) || 42);
  const labels = S.stage1.best.labels;
  for (const w of S.stage2.winners) {
    const docIdx = labels.map((l, i) => l === w.topic ? i : -1).filter(i => i >= 0);
    const sampled = sample(docIdx, 15, rng).map(i => S.stage1.keptRows[i][S.textCol]);
    const card = document.createElement("div");
    card.className = "topic-card";
    card.innerHTML =
      `<h4>Topic ${w.topic}: ${escapeHTML(w.modal_label)}</h4>` +
      `<p class="meta">Modal vote share ${pct(w.modal_share)} (${w.votes_for_modal}/${w.total_votes}) · ` +
      `margin over runner-up ${pct(w.margin_over_runner_up)}${w.modal_share < 0.4 ? " · <strong>fragmented vote — scrutinize</strong>" : ""}</p>` +
      `<p class="meta">Representative words: <code>${escapeHTML(w.words)}</code></p>` +
      `<details><summary>Sampled documents (n=${sampled.length})</summary><ul>` +
      sampled.map(d => `<li>${escapeHTML(d)}</li>`).join("") + `</ul></details>` +
      `<label>Consensus theme <input type="text" class="theme-input" data-topic="${w.topic}" list="theme-list" ` +
      `placeholder="e.g. Sports"></label>` +
      `<label>Reviewer notes <input type="text" class="notes-input" data-topic="${w.topic}" placeholder="primary + senior researcher notes"></label>`;
    box.appendChild(card);
  }
  box.insertAdjacentHTML("beforeend", `<datalist id="theme-list"></datalist>`);
  box.oninput = (e => {
    if (!e.target.classList.contains("theme-input")) return;
    const seen = [...new Set([...box.querySelectorAll(".theme-input")].map(i => i.value.trim()).filter(Boolean))];
    $("theme-list").innerHTML = seen.map(t => `<option value="${escapeHTML(t)}">`).join("");
  });
  $("stage3-body").hidden = false;
  setStageState(3, "idle");
}

function recordConsensus() {
  const inputs = [...$("s3-worksheet").querySelectorAll(".theme-input")];
  const notes = Object.fromEntries([...$("s3-worksheet").querySelectorAll(".notes-input")].map(i => [i.dataset.topic, i.value.trim()]));
  const themeMap = S.stage2.winners.map(w => ({
    topic: w.topic, modal_label: w.modal_label,
    theme: (inputs.find(i => +i.dataset.topic === w.topic)?.value || "").trim(),
    notes: notes[w.topic] || "",
  }));
  const themes = [...new Set(themeMap.map(m => m.theme).filter(Boolean))];
  if (!themes.length) { alert("Enter at least one consensus theme before recording."); return; }
  S.stage3 = { themeMap, themes };
  S.stage4 = S.stage5 = null;
  $("s3-summary").innerHTML =
    `Consensus recorded: <strong>${themes.length} themes</strong> — ${themes.map(escapeHTML).join(" · ")}. ` +
    `${themeMap.filter(m => !m.theme).length} topic(s) left unmapped (treated as noise).`;
  setStageState(3, "done");
  $("run4").disabled = !S.benchmark;
  $("s4-need").hidden = !!S.benchmark;
}

function stage3Downloads(which) {
  if (which === "worksheet") {
    const lines = ["# Stage 3 Review Packet — Theme Synthesis Worksheet", "",
      "Protocol (two-researcher consensus, Theme and Topic system):",
      "1. PRIMARY researcher: read sampled documents per topic, confirm the modal",
      "   LLM label, note overlapping thematic connections — reading against the",
      "   current literature of the target domain.",
      "2. Group topics by conceptual similarity into candidate themes.",
      "3. SENIOR researcher: independently review and critique; reach consensus.",
      "4. Record the consensus in the app and export theme_map.csv.", ""];
    const rng = mulberry32(parseInt($("cfg-seed").value, 10) || 42);
    const labels = S.stage1.best.labels;
    for (const w of S.stage2.winners) {
      const docIdx = labels.map((l, i) => l === w.topic ? i : -1).filter(i => i >= 0);
      const sampled = sample(docIdx, 15, rng).map(i => S.stage1.keptRows[i][S.textCol]);
      lines.push(`## Topic ${w.topic}: ${w.modal_label}`,
        `- Modal vote share: ${pct(w.modal_share)} (${w.votes_for_modal}/${w.total_votes}); margin over runner-up: ${pct(w.margin_over_runner_up)}`,
        `- Representative words: ${w.words}`,
        `- Sampled documents (n=${sampled.length}):`,
        ...sampled.map(d => `    - ${d}`),
        "", "**Primary researcher notes:** ", "**Senior researcher critique:** ", "**Consensus candidate theme:** ", "");
    }
    downloadText("synthesis_worksheet.md", lines.join("\n"), "text/markdown");
  } else if (which === "map") {
    const rows = S.stage3 ? S.stage3.themeMap
      : S.stage2.winners.map(w => ({ topic: w.topic, modal_label: w.modal_label, theme: "", notes: "" }));
    downloadText(S.stage3 ? "theme_map.csv" : "theme_map_TEMPLATE.csv",
      toCSV(rows, ["topic", "modal_label", "theme", "notes"]), "text/csv");
  }
}

/* ------------------------------ stage 4 ---------------------------------- */

function themeDictionaries() {
  // theme dictionary = union of constituent topics' representative words
  const dict = {};
  for (const m of S.stage3.themeMap) {
    if (!m.theme) continue;
    const topic = S.stage1.best.topics.find(t => t.id === m.topic);
    if (!topic) continue;
    (dict[m.theme] = dict[m.theme] || new Set());
    for (const w of topic.words) dict[m.theme].add(w.toLowerCase());
  }
  return dict;
}

function stemMatch(token, dictWord) {
  if (token === dictWord) return true;
  if (token.length >= 4 && dictWord.length >= 4 && (token.startsWith(dictWord) || dictWord.startsWith(token))) return true;
  return token.length >= 5 && dictWord.length >= 5 && token.slice(0, 5) === dictWord.slice(0, 5);
}

function booleanClassify(text, dict) {
  const toks = new Set(String(text).toLowerCase().match(/[a-z]+/g) || []);
  let bestTheme = NONE_LABEL, bestScore = -1;
  for (const [theme, words] of Object.entries(dict)) {
    let score = 0;
    for (const t of toks) if ([...words].some(w => stemMatch(t, w))) score++;
    if (score > bestScore) { bestScore = score; bestTheme = theme; }
  }
  return bestScore >= 2 ? bestTheme : NONE_LABEL;
}

function optionList() { return [...S.stage3.themes, NONE_LABEL]; }

function classifyPrompt(text) {
  const options = optionList();
  const numbered = options.map((o, i) => `${i + 1}. ${o}`).join(", ");
  return `Classify the following text into one of the following ${options.length} themes: ${numbered}.` +
    `Text: ${text}.` +
    `Respond with verbatim classification using only the specified ${options.length} options.`;
}

function canonicalize(raw) {
  const cleaned = raw.replace(/^\s*\d+[.)]\s*/, "").trim().replace(/\.+$/, "").toLowerCase();
  for (const opt of optionList()) {
    if (cleaned === opt.toLowerCase() || cleaned.includes(opt.toLowerCase())) return opt;
  }
  return NONE_LABEL;
}

async function llmClassify(provider, texts, concurrency, progressLabel) {
  const tasks = texts.map(text => async () =>
    canonicalize(await callWithRetries(
      () => provider.chat("You are an expert at classifying text into themes.", classifyPrompt(text), { temperature: 0.5, maxTokens: 30 }),
      5, (err, n, wait) => log("log-4", `API error (${String(err).slice(0, 80)}); retry ${n}/5 in ${wait / 1000}s`, "warn"))));
  return await pool(tasks, concurrency, (done, total) => {
    if (done % 25 === 0 || done === total) $("s4-live").textContent = `${progressLabel}: ${done}/${total}`;
  });
}

async function runStage4() {
  if (!S.stage3 || !S.benchmark) return;
  const threshold = parseFloat($("cfg-threshold").value) || 0.85;
  const concurrency = parseInt($("cfg-concurrency").value, 10) || 6;
  const dict = themeDictionaries();
  const mockHints = {
    themes: Object.fromEntries(Object.entries(dict).map(([t, ws]) => [t, [...ws]])),
    noneLabel: NONE_LABEL,
  };
  let provider;
  try { provider = makeProvider(mockHints); } catch (err) { alert(err.message); return; }
  persistSettings();

  $("run4").disabled = true; setStageState(4, "running");
  $("log-4").innerHTML = ""; $("stage4-results").hidden = true;
  log("log-4", `Benchmarking against ${S.benchmark.length} human-labeled documents… (model: ${provider.label})`);

  const benchRows = S.benchmark.map(b => ({ tweet: b.tweet, human_label: b.human_label }));
  for (const b of benchRows) b.boolean_pred = booleanClassify(b.tweet, dict);
  const llmPreds = await llmClassify(provider, benchRows.map(b => b.tweet), concurrency, "benchmark");
  benchRows.forEach((b, i) => { b.llm_pred = llmPreds[i]; });

  const agree = col => benchRows.filter(b =>
    (b[col] || "").toLowerCase().trim() === (b.human_label || "").toLowerCase().trim()).length / benchRows.length;
  const report = {
    n_benchmark: benchRows.length,
    llm_agreement: +agree("llm_pred").toFixed(4),
    boolean_agreement: +agree("boolean_pred").toFixed(4),
    threshold, model: provider.model,
  };
  log("log-4", `LLM agreement: ${pct(report.llm_agreement)} · Boolean agreement: ${pct(report.boolean_agreement)}`);

  const winner = report.llm_agreement >= report.boolean_agreement
    ? ["llm", report.llm_agreement] : ["boolean", report.boolean_agreement];
  if (winner[1] < threshold) {
    setStageState(4, "blocked");
    S.stage4 = { report, benchRows, classified: null, winner: null };
    $("s4-summary").innerHTML =
      `<span class="fail">Gate refused:</span> best classifier (“${winner[0]}”, ${pct(winner[1])}) is below the ` +
      `${pct(threshold, 0)} agreement threshold. Refine the prompt or theme dictionaries and re-benchmark — ` +
      `the pipeline does not scale an unvalidated classifier.`;
    $("stage4-results").hidden = false;
    $("s4-tables").innerHTML = "";
    $("run4").disabled = false;
    return;
  }
  log("log-4", `Scaling the “${winner[0]}” classifier (${pct(winner[1])} agreement) to ${S.corpus.length.toLocaleString()} documents…`, "best");

  let themes;
  const texts = S.corpus.map(r => r[S.textCol]);
  if (winner[0] === "llm") themes = await llmClassify(provider, texts, concurrency, "corpus");
  else themes = texts.map(t => booleanClassify(t, dict));
  const classified = S.corpus.map((r, i) => ({ ...r, theme: themes[i] }));

  S.stage4 = { report, benchRows, classified, winner: winner[0] };
  S.stage5 = null;
  renderStage4();
  setStageState(4, "done");
  $("run4").disabled = false; $("run5").disabled = false;
  $("s4-live").textContent = "";
}

function renderStage4() {
  const { report, classified, winner } = S.stage4;
  $("stage4-results").hidden = false;
  $("s4-summary").innerHTML =
    `<span class="ok">Gate passed.</span> Scaled the <strong>${winner}</strong> classifier ` +
    `(LLM ${pct(report.llm_agreement)}, Boolean ${pct(report.boolean_agreement)}, threshold ${pct(report.threshold, 0)}). ` +
    `${classified.length.toLocaleString()} documents classified.`;
  const counts = new Map();
  for (const r of classified) counts.set(r.theme, (counts.get(r.theme) || 0) + 1);
  const rows = [...counts.entries()].sort((a, b) => b[1] - a[1]).map(([t, c]) =>
    `<tr><td>${escapeHTML(t)}</td><td>${c.toLocaleString()}</td><td>${pct(c / classified.length)}</td></tr>`).join("");
  $("s4-tables").innerHTML =
    `<table><thead><tr><th>Theme</th><th>Documents</th><th>Share</th></tr></thead><tbody>${rows}</tbody></table>`;
}

function stage4Downloads(which) {
  if (!S.stage4) return;
  if (which === "report") downloadText("benchmark_report.json", JSON.stringify(S.stage4.report, null, 2), "application/json");
  else if (which === "preds") downloadText("benchmark_predictions.csv",
    toCSV(S.stage4.benchRows, ["tweet", "human_label", "boolean_pred", "llm_pred"]), "text/csv");
  else if (which === "corpus" && S.stage4.classified) {
    downloadText("classified_corpus.csv", toCSV(S.stage4.classified), "text/csv");
  }
}

/* ------------------------------ stage 5 ---------------------------------- */

function periodsFromUI() {
  const out = {};
  for (const row of document.querySelectorAll(".period-row")) {
    const name = row.querySelector(".p-name").value.trim();
    const start = row.querySelector(".p-start").value;
    const end = row.querySelector(".p-end").value;
    if (name && start && end) out[name] = [start, end];
  }
  return out;
}

function runStage5() {
  if (!S.stage4?.classified) return;
  const alpha = parseFloat($("cfg-alpha").value) || 0.05;
  const periods = periodsFromUI();
  const classified = S.stage4.classified;
  const themes = S.stage3.themes;
  const hasDate = classified.some(r => r.date);

  setStageState(5, "running");
  let prevRows = [], testRows = [], alphaAdj = null;

  if (hasDate && Object.keys(periods).length >= 2) {
    const inPeriod = classified.map(r => {
      const d = Date.parse(r.date);
      for (const [name, [s, e]] of Object.entries(periods)) {
        if (d >= Date.parse(s) && d <= Date.parse(e) + 86399999) return { ...r, period: name };
      }
      return null;
    }).filter(Boolean);
    const totals = {};
    for (const r of inPeriod) totals[r.period] = (totals[r.period] || 0) + 1;

    const names = Object.keys(periods);
    const pairs = [];
    for (let i = 0; i < names.length; i++) for (let j = i + 1; j < names.length; j++) pairs.push([names[i], names[j]]);
    alphaAdj = alpha / (themes.length * pairs.length);

    for (const theme of themes) {
      const counts = {};
      for (const r of inPeriod) if (r.theme === theme) counts[r.period] = (counts[r.period] || 0) + 1;
      const row = { theme };
      for (const p of names) {
        row[`${p}_pct`] = totals[p] ? +(100 * (counts[p] || 0) / totals[p]).toFixed(2) : null;
        row[`${p}_n`] = totals[p] || 0;
      }
      prevRows.push(row);
      for (const [a, b] of pairs) {
        const [ka, na, kb, nb] = [counts[a] || 0, totals[a] || 0, counts[b] || 0, totals[b] || 0];
        if (!na || !nb) continue;
        const { z, p } = proportionsZTest(ka, na, kb, nb);
        const [pa, pb] = [ka / na, kb / nb];
        testRows.push({
          theme, comparison: `${a} vs ${b}`,
          [`prop_${a}`]: +pa.toFixed(4), [`prop_${b}`]: +pb.toFixed(4),
          pct_change: pa ? +(100 * (pb - pa) / pa).toFixed(1) : null,
          z: +z.toFixed(3), p: p, significant_bonferroni: p < alphaAdj,
        });
      }
    }
    S.stage5 = { prevRows, testRows, alphaAdj, periods: names };
    renderStage5();
  } else {
    S.stage5 = { prevRows: [], testRows: [], alphaAdj: null, periods: [] };
    $("s5-summary").innerHTML = "No usable date column / periods — period tests skipped. LIWC corpora and the GSEM hand-off are still available below.";
    $("s5-chart").innerHTML = ""; $("s5-table").innerHTML = "";
  }
  $("stage5-results").hidden = false;
  setStageState(5, "done");
}

function renderStage5() {
  const { prevRows, testRows, alphaAdj, periods } = S.stage5;
  $("s5-summary").innerHTML =
    `Bonferroni-adjusted α = ${(parseFloat($("cfg-alpha").value) || 0.05)} / ` +
    `(${S.stage3.themes.length} themes × ${testRows.length / S.stage3.themes.length || 0} tests) = <strong>${alphaAdj?.toFixed(4)}</strong>. ` +
    `${testRows.filter(t => t.significant_bonferroni).length} of ${testRows.length} comparisons significant.`;
  groupedBarChart($("s5-chart"), {
    groups: prevRows.map(r => r.theme),
    series: periods,
    values: prevRows.map(r => periods.map(p => r[`${p}_pct`])),
  });
  const head = `<tr><th>Theme</th><th>Comparison</th><th>Δ%</th><th>z</th><th>p</th><th>Significant</th></tr>`;
  const rows = testRows.map(t =>
    `<tr><td>${escapeHTML(t.theme)}</td><td>${escapeHTML(t.comparison)}</td>` +
    `<td>${t.pct_change == null ? "—" : t.pct_change + "%"}</td><td>${t.z}</td>` +
    `<td>${t.p < 0.0001 ? t.p.toExponential(2) : t.p.toFixed(4)}</td>` +
    `<td>${t.significant_bonferroni ? "<strong>yes</strong>" : "no"}</td></tr>`).join("");
  $("s5-table").innerHTML = `<table><thead>${head}</thead><tbody>${rows}</tbody></table>`;
}

const STATA_DO = `* crosslagged_gsem.do — generated by the TopicLLM browser pipeline
* Cross-lagged panel model (reference specification):
*   exposure_t1/t2 : z-standardized potential-exposure indices (continuous)
*   usergen_t1/t2  : binary indicators of user-generated theme content
* Expected input: a per-account CSV with those four columns.

import delimited "crosslagged_input.csv", clear

egen z_exp_t1 = std(exposure_t1)
egen z_exp_t2 = std(exposure_t2)

gsem (z_exp_t2  <- z_exp_t1 usergen_t1, family(gaussian) link(identity)) ///
     (usergen_t2 <- usergen_t1 z_exp_t1, family(bernoulli) link(logit)),  ///
     vce(robust)

estat ic
`;

function stage5Downloads(which) {
  if (which === "prev" && S.stage5) downloadText("prevalence_by_period.csv", toCSV(S.stage5.prevRows), "text/csv");
  else if (which === "ztest" && S.stage5) downloadText("ztest_results.csv", toCSV(S.stage5.testRows), "text/csv");
  else if (which === "liwc" && S.stage4?.classified) {
    const files = {};
    for (const theme of S.stage3.themes) {
      const texts = S.stage4.classified.filter(r => r.theme === theme).map(r => r[S.textCol]);
      files[`liwc_corpora/${slug(theme)}.txt`] = texts.join("\n");
    }
    downloadBlob("liwc_corpora.zip", buildZip(files));
  } else if (which === "stata") downloadText("crosslagged_gsem.do", STATA_DO);
}

/* --------------------------- session archive ----------------------------- */

function downloadSessionArchive() {
  const files = {};
  const add = (name, content) => { if (content != null) files[name] = content; };
  if (S.stage1) {
    add("stage1/all_iteration_results.json", JSON.stringify({ seed: stage1Config().randomSeed, embedder: S.stage1.embedderUsed, iterations: S.stage1.allIterations }, null, 2));
    add("stage1/best_model/parameters.json", JSON.stringify({
      umap_params: S.stage1.best.umapParams, hdbscan_params: S.stage1.best.hdbParams,
      n_topics: S.stage1.best.nTopics, coherence: S.stage1.best.coherence,
    }, null, 2));
    add("stage1/topics_for_naming.csv", toCSV(S.stage1.topicsForNaming, ["topic", "words"]));
    add("stage1/best_model/classified_tweets.csv", toCSV(S.stage1.keptRows.map((r, i) => ({
      [S.textCol]: r[S.textCol], date: r.date || "", preprocessed: r.preprocessed, topic: S.stage1.best.labels[i],
    }))));
  }
  if (S.stage2) {
    add("stage2/vote_log.csv", toCSV(S.stage2.ballots, ["topic", "vote_index", "label"]));
    add("stage2/topic_names.csv", toCSV(S.stage2.winners, ["topic", "words", "modal_label", "votes_for_modal", "total_votes", "modal_share", "margin_over_runner_up"]));
  }
  if (S.stage3) add("stage3/theme_map.csv", toCSV(S.stage3.themeMap, ["topic", "modal_label", "theme", "notes"]));
  if (S.stage4) {
    add("stage4/benchmark_report.json", JSON.stringify(S.stage4.report, null, 2));
    add("stage4/benchmark_predictions.csv", toCSV(S.stage4.benchRows, ["tweet", "human_label", "boolean_pred", "llm_pred"]));
    if (S.stage4.classified) add("stage4/classified_corpus.csv", toCSV(S.stage4.classified));
  }
  if (S.stage5) {
    add("stage5/prevalence_by_period.csv", toCSV(S.stage5.prevRows));
    add("stage5/ztest_results.csv", toCSV(S.stage5.testRows));
    add("stage5/crosslagged_gsem.do", STATA_DO);
    if (S.stage4?.classified && S.stage3) {
      for (const theme of S.stage3.themes) {
        add(`stage5/liwc_corpora/${slug(theme)}.txt`,
          S.stage4.classified.filter(r => r.theme === theme).map(r => r[S.textCol]).join("\n"));
      }
    }
  }
  if (!Object.keys(files).length) { alert("Nothing to archive yet — run at least Stage 1."); return; }
  downloadBlob("pipeline_output.zip", buildZip(files));
}

/* ------------------------------- tabs ------------------------------------ */

function initTabs() {
  const tabs = document.querySelectorAll("nav.tabs button");
  tabs.forEach(btn => btn.addEventListener("click", () => {
    tabs.forEach(b => b.classList.toggle("active", b === btn));
    document.querySelectorAll("main > section.tab").forEach(sec =>
      sec.hidden = sec.id !== "tab-" + btn.dataset.tab);
  }));
}

/* ------------------------------- init ------------------------------------ */

document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  restoreSettings();
  summarizeData();
  $("stopwords").value = DEFAULT_STOPWORDS;

  on("btn-demo", "click", loadDemo);
  on("file-corpus", "change", e => e.target.files[0] && loadCorpusFile(e.target.files[0]));
  on("file-benchmark", "change", e => e.target.files[0] && loadBenchmarkFile(e.target.files[0]));
  on("llm-provider", "change", syncProviderUI);

  on("run1", "click", runStage1);
  on("cancel1", "click", cancelStage1);
  on("run2", "click", runStage2);
  on("btn-consensus", "click", recordConsensus);
  on("run4", "click", runStage4);
  on("run5", "click", runStage5);
  on("btn-archive", "click", downloadSessionArchive);

  document.querySelectorAll("[data-dl]").forEach(btn => btn.addEventListener("click", () => {
    const [stage, which] = btn.dataset.dl.split(":");
    ({ 1: stage1Downloads, 2: stage2Downloads, 3: stage3Downloads, 4: stage4Downloads, 5: stage5Downloads })[stage](which);
  }));
});
