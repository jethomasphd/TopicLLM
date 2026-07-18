/* worker1.js — Stage 1 (coherence-optimized topic discovery) as a module
 * Web Worker, so the randomized search never blocks the UI.
 *
 * Search logic mirrors stage1_topic_discovery.py: seeded random draws over
 * the UMAP/HDBSCAN spaces; every sampled configuration is evaluated across
 * all achievable topic solutions in [topicMin, topicMax]; every model is
 * scored with c_v coherence; the audit trail records all of it.
 */

import { mulberry32, choice } from "./util.js";
import { buildStopwords, preprocessCorpus } from "./preprocess.js";
import { embedMiniLM, embedHashed, cosineDistance } from "./embed.js";
import { hdbscan } from "./hdbscan.js";
import { tokenizeDoc, topicSolutions } from "./model.js";
import { createCoherenceContext, cvCoherence } from "./coherence.js";

let UMAPClass = null;

async function loadUMAP() {
  if (UMAPClass) return UMAPClass;
  const code = await (await fetch(new URL("../vendor/umap-js.min.js", import.meta.url))).text();
  new Function(code).call(self);       // UMD attaches self.UMAP
  UMAPClass = self.UMAP.UMAP;
  return UMAPClass;
}

const post = (type, data) => self.postMessage({ type, ...data });

self.onmessage = async (e) => {
  try {
    await runStage1(e.data);
  } catch (err) {
    post("error", { message: String(err && err.stack || err) });
  }
};

async function runStage1({ rows, textCol, customStopwords, config }) {
  const cfg = config;
  const t0 = Date.now();

  // ---- preprocess ---------------------------------------------------------
  post("status", { text: `Preprocessing ${rows.length.toLocaleString()} documents…` });
  const stopwords = buildStopwords(customStopwords);
  const kept = preprocessCorpus(rows, textCol, stopwords);
  post("status", { text: `${kept.length.toLocaleString()} non-empty documents retained.` });
  const docs = kept.map(r => r.preprocessed);
  const tokenized = docs.map(tokenizeDoc);

  // ---- embed once, reuse across all candidate models ----------------------
  let embeddings, embedderUsed = cfg.embedder;
  if (cfg.embedder === "minilm") {
    try {
      post("status", { text: "Loading all-MiniLM-L6-v2 (downloads once, runs locally)…" });
      embeddings = await embedMiniLM(docs, txt => post("status", { text: txt }));
    } catch (err) {
      post("status", { text: `MiniLM unavailable (${String(err).slice(0, 120)}…) — falling back to hashed embeddings.`, level: "warn" });
      embedderUsed = "hashed";
    }
  }
  if (!embeddings) {
    post("status", { text: "Computing hashed bag-of-words embeddings (offline mode)…" });
    embeddings = embedHashed(docs, txt => post("status", { text: txt }));
    embedderUsed = "hashed";
  }

  // ---- randomized search --------------------------------------------------
  const UMAP = await loadUMAP();
  const rng = mulberry32(cfg.randomSeed);
  const allIterations = [];
  let best = null;   // { iteration, umap, hdbscan, nTopics, coherence, labels, topics }
  const coherenceCtx = createCoherenceContext(tokenized);

  for (let it = 1; it <= cfg.searchIterations; it++) {
    const umapParams = {
      n_neighbors: choice(cfg.umapSpace.n_neighbors, rng),
      n_components: choice(cfg.umapSpace.n_components, rng),
      min_dist: choice(cfg.umapSpace.min_dist, rng),
      metric: "cosine",
    };
    const hdbParams = {
      min_cluster_size: choice(cfg.hdbscanSpace.min_cluster_size, rng),
      metric: "euclidean",
      cluster_selection_method: "eom",
    };
    post("iteration", { iteration: it, total: cfg.searchIterations, umapParams, hdbParams });

    let results = [];
    try {
      const reducer = new UMAP({
        nComponents: umapParams.n_components,
        nNeighbors: Math.min(umapParams.n_neighbors, docs.length - 1),
        minDist: umapParams.min_dist,
        spread: 1.0,
        distanceFn: cosineDistance,
        random: mulberry32(cfg.randomSeed * 1000 + it),
      });
      const reduced = await reducer.fitAsync(embeddings.map(v => Array.from(v)));
      const labels = hdbscan(reduced, hdbParams.min_cluster_size);
      const nClusters = new Set(Array.from(labels).filter(l => l !== -1)).size;
      post("status", { text: `Iteration ${it}: HDBSCAN found ${nClusters} raw clusters.` });

      const solutions = topicSolutions(tokenized, labels,
        { topicMin: cfg.topicMin, topicMax: cfg.topicMax });
      for (const sol of solutions) {
        if (sol.topics.length < 2) continue;
        const coherence = cvCoherence(sol.topics.map(t => t.words), coherenceCtx);
        if (!isFinite(coherence)) continue;
        results.push([sol.nTopics, coherence]);
        post("model", { iteration: it, nTopics: sol.nTopics, coherence });
        if (!best || coherence > best.coherence) {
          best = {
            iteration: it, umapParams, hdbParams,
            nTopics: sol.nTopics, coherence,
            labels: Array.from(sol.labels),
            topics: sol.topics,
          };
          post("best", { iteration: it, nTopics: sol.nTopics, coherence });
        }
      }
    } catch (err) {
      post("status", { text: `Iteration ${it} failed: ${String(err).slice(0, 160)}`, level: "warn" });
    }
    results.sort((a, b) => a[0] - b[0]);
    allIterations.push({
      iteration: it, umap_params: umapParams, hdbscan_params: hdbParams,
      results, max_coherence: results.length ? Math.max(...results.map(r => r[1])) : null,
    });
  }

  if (!best) { post("error", { message: "No valid models across all iterations — check data/parameters." }); return; }

  const bestIter = allIterations.find(a => a.iteration === best.iteration);
  post("done", {
    payload: {
      embedderUsed,
      elapsedMs: Date.now() - t0,
      keptRows: kept,
      allIterations,
      best,
      coherenceCurve: bestIter ? bestIter.results : [],
      topicsForNaming: best.topics.map(t => ({ topic: t.id, words: t.words.join(", ") })),
    },
  });
}
