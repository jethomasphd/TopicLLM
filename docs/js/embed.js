/* embed.js — Sentence embeddings in the browser.
 *
 * Primary: all-MiniLM-L6-v2 (the model named in the paper) via
 * transformers.js, running locally on WebAssembly/WebGPU. The model
 * (~25 MB) is downloaded once from the Hugging Face Hub and cached by the
 * browser. Fallback: a deterministic hashed bag-of-words embedder that
 * needs no download — lower quality, useful for demos and offline runs.
 */

import { mulberry32, fnv1a } from "./util.js";

const TRANSFORMERS_CDN = "https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.7.1";
const MINILM_ID = "Xenova/all-MiniLM-L6-v2";

let _extractor = null;

/** Load transformers.js + MiniLM. Throws if the CDN/model is unreachable. */
export async function loadMiniLM(onProgress) {
  if (_extractor) return _extractor;
  const { pipeline, env } = await import(/* webpackIgnore: true */ TRANSFORMERS_CDN);
  env.allowLocalModels = false;
  _extractor = await pipeline("feature-extraction", MINILM_ID, {
    dtype: "q8",
    progress_callback: p => {
      if (onProgress && p.status === "progress" && p.total) {
        onProgress(`downloading ${p.file}: ${Math.round(100 * p.loaded / p.total)}%`);
      }
    },
  });
  return _extractor;
}

/** Embed docs with MiniLM (mean pooling, L2-normalized), batched. */
export async function embedMiniLM(docs, onProgress) {
  const extractor = await loadMiniLM(onProgress);
  const out = [];
  const BATCH = 16;
  for (let i = 0; i < docs.length; i += BATCH) {
    const batch = docs.slice(i, i + BATCH);
    const res = await extractor(batch, { pooling: "mean", normalize: true });
    const [n, dim] = res.dims;
    for (let r = 0; r < n; r++) out.push(Float32Array.from(res.data.slice(r * dim, (r + 1) * dim)));
    const done = Math.min(i + BATCH, docs.length);
    if (onProgress) onProgress(`embedding ${done}/${docs.length}`, done / docs.length);
  }
  return out;
}

/* ---------------- Fallback: hashed bag-of-words embedder ----------------- */

const HASH_DIM = 384;
const _wordVecCache = new Map();

function wordVector(word) {
  let v = _wordVecCache.get(word);
  if (v) return v;
  const rng = mulberry32(fnv1a(word));
  v = new Float32Array(HASH_DIM);
  for (let i = 0; i < HASH_DIM; i++) v[i] = rng() * 2 - 1;
  // include character-trigram signal so related word forms land nearby
  for (let t = 0; t + 3 <= word.length; t++) {
    const rng3 = mulberry32(fnv1a("tri:" + word.slice(t, t + 3)));
    for (let i = 0; i < HASH_DIM; i++) v[i] += 0.35 * (rng3() * 2 - 1);
  }
  let norm = 0;
  for (let i = 0; i < HASH_DIM; i++) norm += v[i] * v[i];
  norm = Math.sqrt(norm) || 1;
  for (let i = 0; i < HASH_DIM; i++) v[i] /= norm;
  _wordVecCache.set(word, v);
  return v;
}

/** Deterministic hashed embeddings (no network, no model download). */
export function embedHashed(docs, onProgress) {
  const out = [];
  for (let d = 0; d < docs.length; d++) {
    const tokens = docs[d].split(/\s+/).filter(Boolean);
    const counts = new Map();
    for (const t of tokens) counts.set(t, (counts.get(t) || 0) + 1);
    const v = new Float32Array(HASH_DIM);
    for (const [word, c] of counts) {
      const wv = wordVector(word);
      const w = 1 + Math.log(c);
      for (let i = 0; i < HASH_DIM; i++) v[i] += w * wv[i];
    }
    let norm = 0;
    for (let i = 0; i < HASH_DIM; i++) norm += v[i] * v[i];
    norm = Math.sqrt(norm) || 1;
    for (let i = 0; i < HASH_DIM; i++) v[i] /= norm;
    out.push(v);
    if (onProgress && (d + 1) % 200 === 0) onProgress(`embedding ${d + 1}/${docs.length}`, (d + 1) / docs.length);
  }
  return out;
}

/** Cosine distance for unit-normalized vectors. */
export function cosineDistance(a, b) {
  let dot = 0;
  for (let i = 0; i < a.length; i++) dot += a[i] * b[i];
  return 1 - dot;
}
