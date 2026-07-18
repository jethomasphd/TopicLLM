/* model.js — BERTopic-style topic assembly in JavaScript:
 * class-based TF-IDF term weighting (Grootendorst, 2022) and iterative
 * topic reduction, evaluated across maximum-topic solutions.
 */

/** Tokenize a preprocessed doc (stopwords were removed in preprocessing). */
export function tokenizeDoc(doc) {
  return doc.split(/\s+/).filter(t => t.length >= 2);
}

function addCounts(target, source) {
  for (const [w, c] of source) target.set(w, (target.get(w) || 0) + c);
}

/** c-TF-IDF scores for a set of classes.
 *  @param {Map<string,number>[]} classCounts word counts per class
 *  @returns {Map<string,number>[]} score maps per class */
function cTfIdf(classCounts) {
  const df = new Map();          // total frequency of each word across classes
  let totalWords = 0;
  for (const counts of classCounts) {
    for (const [w, c] of counts) { df.set(w, (df.get(w) || 0) + c); totalWords += c; }
  }
  const A = totalWords / classCounts.length;   // average words per class
  const idf = new Map();
  for (const [w, f] of df) idf.set(w, Math.log(1 + A / f));
  return classCounts.map(counts => {
    let classTotal = 0;
    for (const c of counts.values()) classTotal += c;
    const scores = new Map();
    for (const [w, c] of counts) scores.set(w, (c / (classTotal || 1)) * idf.get(w));
    return scores;
  });
}

function topWords(scoreMap, k = 10) {
  return [...scoreMap.entries()].sort((a, b) => b[1] - a[1]).slice(0, k).map(e => e[0]);
}

function cosineSim(a, b) {
  let dot = 0, na = 0, nb = 0;
  const [small, big] = a.size <= b.size ? [a, b] : [b, a];
  for (const [w, va] of small) { const vb = big.get(w); if (vb !== undefined) dot += va * vb; }
  for (const v of a.values()) na += v * v;
  for (const v of b.values()) nb += v * v;
  return dot / (Math.sqrt(na * nb) || 1);
}

/**
 * From HDBSCAN labels, produce topic solutions at every achievable topic
 * count in [topicMin, topicMax] by iterative reduction: repeatedly merge the
 * least frequent topic into its most c-TF-IDF-similar neighbor (BERTopic's
 * nr_topics behavior). The noise cluster (-1) is never merged or named.
 *
 * @returns array of { nTopics, labels: Int32Array, topics: [{id, size, words}] }
 */
export function topicSolutions(tokenized, labels, { topicMin = 2, topicMax = 25, nWords = 10 }) {
  const n = tokenized.length;
  // ---- base clusters from HDBSCAN labels ---------------------------------
  const byLabel = new Map();
  for (let i = 0; i < n; i++) {
    const lab = labels[i];
    if (lab === -1) continue;
    if (!byLabel.has(lab)) byLabel.set(lab, []);
    byLabel.get(lab).push(i);
  }
  let clusters = [...byLabel.values()].map(docIdx => {
    const counts = new Map();
    for (const d of docIdx) {
      for (const t of tokenized[d]) counts.set(t, (counts.get(t) || 0) + 1);
    }
    return { docIdx, counts };
  });
  const solutions = [];
  if (clusters.length < 2) return solutions;

  const record = () => {
    const order = clusters.map((c, i) => i).sort((a, b) => clusters[b].docIdx.length - clusters[a].docIdx.length);
    const scores = cTfIdf(clusters.map(c => c.counts));
    const lab = new Int32Array(n).fill(-1);
    const topics = order.map((ci, rank) => {
      for (const d of clusters[ci].docIdx) lab[d] = rank;
      return { id: rank, size: clusters[ci].docIdx.length, words: topWords(scores[ci], nWords) };
    });
    solutions.push({ nTopics: clusters.length, labels: lab, topics });
  };

  const mergeOnce = () => {
    const scores = cTfIdf(clusters.map(c => c.counts));
    let smallest = 0;
    for (let i = 1; i < clusters.length; i++) {
      if (clusters[i].docIdx.length < clusters[smallest].docIdx.length) smallest = i;
    }
    let bestSim = -Infinity, target = -1;
    for (let i = 0; i < clusters.length; i++) {
      if (i === smallest) continue;
      const sim = cosineSim(scores[smallest], scores[i]);
      if (sim > bestSim) { bestSim = sim; target = i; }
    }
    clusters[target].docIdx.push(...clusters[smallest].docIdx);
    addCounts(clusters[target].counts, clusters[smallest].counts);
    clusters.splice(smallest, 1);
  };

  while (clusters.length > topicMax) mergeOnce();       // above range: reduce silently
  while (clusters.length >= Math.max(2, topicMin)) {
    record();
    if (clusters.length === Math.max(2, topicMin)) break;
    mergeOnce();
  }
  return solutions;
}
