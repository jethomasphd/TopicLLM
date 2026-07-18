/* coherence.js — c_v topic coherence (Röder, Both & Hinneburg, 2015),
 * mirroring Gensim's CoherenceModel(coherence="c_v"): boolean sliding
 * window (size 110), NPMI confirmation with one-set segmentation, and
 * cosine similarity of context vectors, averaged over words then topics.
 */

const EPS = 1e-12;
const WINDOW = 110;

/** Build a reusable occurrence index over the corpus's virtual windows. */
export function createCoherenceContext(tokenizedDocs, windowSize = WINDOW) {
  // window layout: docs shorter than the window contribute one window;
  // longer docs contribute len - windowSize + 1 sliding windows.
  const windowsPerDoc = tokenizedDocs.map(t =>
    t.length <= windowSize ? 1 : t.length - windowSize + 1);
  let totalWindows = 0;
  const windowOffset = windowsPerDoc.map(w => { const o = totalWindows; totalWindows += w; return o; });

  const cache = new Map();       // word -> Set(window index)
  const pairCache = new Map();   // "a|b" -> joint window count

  function occurrences(word) {
    let set = cache.get(word);
    if (set) return set;
    set = new Set();
    for (let d = 0; d < tokenizedDocs.length; d++) {
      const toks = tokenizedDocs[d];
      if (toks.length <= windowSize) {
        if (toks.includes(word)) set.add(windowOffset[d]);
      } else {
        // positions of the word, then mark every window covering a position
        for (let p = 0; p < toks.length; p++) {
          if (toks[p] !== word) continue;
          const first = Math.max(0, p - windowSize + 1);
          const last = Math.min(p, toks.length - windowSize);
          for (let w = first; w <= last; w++) set.add(windowOffset[d] + w);
        }
      }
    }
    cache.set(word, set);
    return set;
  }

  function jointCount(a, b) {
    const key = a < b ? a + "|" + b : b + "|" + a;
    let c = pairCache.get(key);
    if (c !== undefined) return c;
    const sa = occurrences(a), sb = occurrences(b);
    const [small, big] = sa.size <= sb.size ? [sa, sb] : [sb, sa];
    c = 0;
    for (const w of small) if (big.has(w)) c++;
    pairCache.set(key, c);
    return c;
  }

  return { totalWindows, occurrences, jointCount };
}

function npmi(ctx, a, b) {
  const W = ctx.totalWindows;
  const pa = ctx.occurrences(a).size / W;
  const pb = ctx.occurrences(b).size / W;
  const pab = ctx.jointCount(a, b) / W;
  if (pa === 0 || pb === 0) return 0;
  return Math.log((pab + EPS) / (pa * pb)) / -Math.log(pab + EPS);
}

/** c_v coherence of a list of topics (each an array of top words). */
export function cvCoherence(topicWordLists, ctx) {
  const perTopic = [];
  for (const words of topicWordLists) {
    const W = words.filter(w => ctx.occurrences(w).size > 0);
    if (W.length < 2) continue;
    // context vector of each word against the full set (one-set segmentation)
    const vectors = W.map(wi => W.map(wj => npmi(ctx, wi, wj)));
    const sumVec = new Array(W.length).fill(0);
    for (const v of vectors) for (let i = 0; i < v.length; i++) sumVec[i] += v[i];
    let topicScore = 0;
    for (const v of vectors) {
      let dot = 0, na = 0, nb = 0;
      for (let i = 0; i < v.length; i++) { dot += v[i] * sumVec[i]; na += v[i] * v[i]; nb += sumVec[i] * sumVec[i]; }
      topicScore += na && nb ? dot / Math.sqrt(na * nb) : 0;
    }
    perTopic.push(topicScore / vectors.length);
  }
  if (!perTopic.length) return NaN;
  return perTopic.reduce((s, x) => s + x, 0) / perTopic.length;
}
