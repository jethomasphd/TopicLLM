/* hdbscan.js — HDBSCAN (Campello, Moulavi & Sander, 2013) in JavaScript.
 *
 * Faithful port of the reference algorithm as used by the Python pipeline:
 * Euclidean metric, excess-of-mass (eom) cluster selection,
 * min_samples = min_cluster_size (the hdbscan library default).
 *
 * Steps: core distances -> mutual-reachability -> MST (Prim) ->
 * single-linkage hierarchy -> condensed tree -> stability -> EOM selection.
 * Points outside every selected cluster are labeled -1 (noise).
 */

function euclidean(a, b) {
  let s = 0;
  for (let i = 0; i < a.length; i++) { const d = a[i] - b[i]; s += d * d; }
  return Math.sqrt(s);
}

/** @param {Float32Array[]|number[][]} points  low-dimensional embeddings
 *  @param {number} minClusterSize
 *  @returns {Int32Array} labels (-1 = noise, clusters numbered arbitrarily) */
export function hdbscan(points, minClusterSize) {
  const n = points.length;
  if (n === 0) return new Int32Array(0);
  const minSamples = minClusterSize;

  // ---- pairwise distances + core distances --------------------------------
  const dist = new Float32Array(n * n);
  for (let i = 0; i < n; i++) {
    for (let j = i + 1; j < n; j++) {
      const d = euclidean(points[i], points[j]);
      dist[i * n + j] = d; dist[j * n + i] = d;
    }
  }
  const core = new Float32Array(n);
  const rowBuf = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    rowBuf.set(dist.subarray(i * n, i * n + n));
    const sorted = Array.from(rowBuf).sort((a, b) => a - b);
    core[i] = sorted[Math.min(minSamples, n - 1)]; // row includes self at 0
  }

  // ---- MST over the mutual-reachability graph (Prim) ----------------------
  const inTree = new Uint8Array(n);
  const minEdge = new Float32Array(n).fill(Infinity);
  const minFrom = new Int32Array(n).fill(-1);
  const edges = []; // [a, b, mrDistance]
  let current = 0;
  inTree[0] = 1;
  for (let added = 1; added < n; added++) {
    for (let j = 0; j < n; j++) {
      if (inTree[j]) continue;
      const mr = Math.max(core[current], core[j], dist[current * n + j]);
      if (mr < minEdge[j]) { minEdge[j] = mr; minFrom[j] = current; }
    }
    let best = -1, bestD = Infinity;
    for (let j = 0; j < n; j++) {
      if (!inTree[j] && minEdge[j] < bestD) { bestD = minEdge[j]; best = j; }
    }
    edges.push([minFrom[best], best, bestD]);
    inTree[best] = 1; current = best;
  }
  edges.sort((a, b) => a[2] - b[2]);

  // ---- single-linkage hierarchy (union-find over sorted MST edges) --------
  // Node ids: 0..n-1 points; n..2n-2 merge nodes.
  const parentUF = new Int32Array(2 * n - 1);
  for (let i = 0; i < parentUF.length; i++) parentUF[i] = i;
  const find = x => { while (parentUF[x] !== x) { parentUF[x] = parentUF[parentUF[x]]; x = parentUF[x]; } return x; };
  const left = new Int32Array(n - 1), right = new Int32Array(n - 1);
  const mergeDist = new Float32Array(n - 1), nodeSize = new Int32Array(2 * n - 1).fill(1);
  let nextNode = n;
  for (const [a, b, d] of edges) {
    const ra = find(a), rb = find(b);
    const id = nextNode - n;
    left[id] = ra; right[id] = rb; mergeDist[id] = d;
    nodeSize[nextNode] = nodeSize[ra] + nodeSize[rb];
    parentUF[ra] = nextNode; parentUF[rb] = nextNode;
    nextNode++;
  }

  // ---- condense the tree --------------------------------------------------
  // Condensed clusters are numbered from 0 (root). For each cluster we store
  // its birth lambda, its point "fall-out" events, and child clusters.
  const EPS = 1e-12;
  const lambdaOf = d => 1 / Math.max(d, EPS);
  const clusters = [{ birth: 0, children: [], points: [], pointLambdas: [] }];
  /** collect all leaf points under hierarchy node id */
  const collectPoints = (node) => {
    const out = [], stack = [node];
    while (stack.length) {
      const x = stack.pop();
      if (x < n) out.push(x);
      else { stack.push(left[x - n], right[x - n]); }
    }
    return out;
  };

  const root = 2 * n - 2;
  // stack entries: [hierarchyNode, condensedClusterId]
  const stack = [[root, 0]];
  while (stack.length) {
    const [node, cid] = stack.pop();
    if (node < n) { // singleton point falls out of its cluster at birth lambda
      clusters[cid].points.push(node);
      clusters[cid].pointLambdas.push(clusters[cid].birth);
      continue;
    }
    const id = node - n;
    const lam = lambdaOf(mergeDist[id]);
    const l = left[id], r = right[id];
    const sizeL = nodeSize[l], sizeR = nodeSize[r];
    if (sizeL >= minClusterSize && sizeR >= minClusterSize) {
      // true split: two new condensed clusters born at lam
      for (const child of [l, r]) {
        const newId = clusters.length;
        clusters.push({ birth: lam, children: [], points: [], pointLambdas: [], parent: cid });
        clusters[cid].children.push(newId);
        stack.push([child, newId]);
      }
    } else if (sizeL < minClusterSize && sizeR < minClusterSize) {
      // both sides fall out of cid at lam
      for (const p of collectPoints(node)) {
        clusters[cid].points.push(p);
        clusters[cid].pointLambdas.push(lam);
      }
    } else {
      // the small side falls out; the big side continues as cid
      const [big, small] = sizeL >= minClusterSize ? [l, r] : [r, l];
      for (const p of collectPoints(small)) {
        clusters[cid].points.push(p);
        clusters[cid].pointLambdas.push(lam);
      }
      stack.push([big, cid]);
    }
  }

  // ---- stability + excess-of-mass selection -------------------------------
  const nc = clusters.length;
  const stability = new Float64Array(nc);
  for (let c = 0; c < nc; c++) {
    const cl = clusters[c];
    let s = 0;
    for (let i = 0; i < cl.points.length; i++) s += cl.pointLambdas[i] - cl.birth;
    for (const ch of cl.children) s += (clusters[ch].birth - cl.birth) * countPoints(ch);
    stability[c] = s;
  }
  function countPoints(c) {
    let total = clusters[c].points.length;
    for (const ch of clusters[c].children) total += countPoints(ch);
    return total;
  }

  const selected = new Uint8Array(nc);
  const subtreeStability = new Float64Array(nc);
  // process leaves-first (children always have higher ids than parents here)
  for (let c = nc - 1; c >= 0; c--) {
    const cl = clusters[c];
    if (cl.children.length === 0) {
      subtreeStability[c] = stability[c];
      selected[c] = c === 0 ? 0 : 1; // a childless root means no real clusters
    } else {
      let childSum = 0;
      for (const ch of cl.children) childSum += subtreeStability[ch];
      if (childSum > stability[c] || c === 0) { // root never selected
        subtreeStability[c] = childSum;
        selected[c] = 0;
      } else {
        subtreeStability[c] = stability[c];
        selected[c] = 1;
        // deselect entire subtree below
        const st = [...cl.children];
        while (st.length) {
          const x = st.pop();
          selected[x] = 0;
          st.push(...clusters[x].children);
        }
      }
    }
  }

  // ---- labels -------------------------------------------------------------
  const labels = new Int32Array(n).fill(-1);
  let nextLabel = 0;
  for (let c = 0; c < nc; c++) {
    if (!selected[c]) continue;
    const lab = nextLabel++;
    const st = [c];
    while (st.length) {
      const x = st.pop();
      for (const p of clusters[x].points) labels[p] = lab;
      st.push(...clusters[x].children);
    }
  }
  return labels;
}
