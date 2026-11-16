/* Pure, shared research safeguards. No UI or network side effects. */
import { proportionsZTest } from './stats.js';
export const NONE = 'The text does not fit into any of these themes';
export const INVALID = '__INVALID_RESPONSE__';
export const API_ERROR = '__API_ERROR__';

export function canonicalLabel(raw, themes) {
  if (raw === API_ERROR || String(raw).startsWith('Error:')) return { label: API_ERROR, status: 'error' };
  const options = [...themes, NONE];
  const cleaned = String(raw).trim().replace(/^['"“”]|['"“”]$/g, '').replace(/\.$/, '').trim();
  if (/^\d+$/.test(cleaned) && +cleaned > 0 && +cleaned <= options.length) return {label: options[+cleaned - 1], status: 'matched'};
  const plain = cleaned.replace(/^\d+[.)]\s*/, '').replace(/^theme:\s*/i, '').toLowerCase();
  const exact = options.find(x => x.toLowerCase() === plain);
  return exact ? {label: exact, status: 'matched'} : {label: INVALID, status: 'unmatched'};
}

export function validateBenchmark(rows, themes) {
  if (!rows.length) throw new Error('The benchmark is empty. Add independently labeled documents.');
  const labels = new Set([...themes, NONE]);
  const bad = rows.filter(r => !String(r.tweet || '').trim() || !labels.has(r.human_label));
  if (bad.length) throw new Error(`${bad.length} benchmark rows have missing text or labels outside the agreed themes. Check the CSV before making LLM calls.`);
}

export function scoreLabels(truth, predictions, labels) {
  if (!truth.length || truth.length !== predictions.length) throw new Error('Benchmark arrays must be non-empty and aligned.');
  const n = truth.length, all = [...new Set([...labels, ...truth, ...predictions])];
  const confusion = Object.fromEntries(all.map(a => [a, Object.fromEntries(all.map(b => [b, 0]))]));
  truth.forEach((t, i) => confusion[t][predictions[i]]++);
  const agreement = truth.filter((t, i) => t === predictions[i]).length / n;
  const count = (xs, label) => xs.filter(x => x === label).length;
  const pe = all.reduce((s, x) => s + count(truth, x) * count(predictions, x), 0) / n ** 2;
  const per_label = Object.fromEntries(labels.map(label => {
    const human_n = count(truth, label), pred_n = count(predictions, label), tp = confusion[label][label];
    return [label, {human_n, pred_n, precision: pred_n ? tp / pred_n : null, recall: human_n ? tp / human_n : null}];
  }));
  return {n, agreement, cohens_kappa: pe < 1 ? (agreement - pe) / (1 - pe) : null, per_label, confusion};
}

export function validatePeriods(periods) {
  const entries = Object.entries(periods);
  if (entries.length < 2) throw new Error('Define at least two time periods.');
  const validDate = d => /^\d{4}-\d{2}-\d{2}$/.test(d) && Number.isFinite(Date.parse(d)) && new Date(d).toISOString().slice(0,10) === d;
  for (const [name, [a, b]] of entries) {
    if (!name || !validDate(a) || !validDate(b) || a > b) throw new Error(`Invalid dates for period ${name}.`);
  }
  for (let i = 0; i < entries.length; i++) for (let j = i + 1; j < entries.length; j++) {
    if (entries[i][1][0] <= entries[j][1][1] && entries[j][1][0] <= entries[i][1][1]) throw new Error('Periods overlap. Use non-overlapping date ranges.');
  }
  return entries;
}

export function estimatePrevalence(classified, themes, periods, alpha = .05) {
  if (!classified.length || !themes.length) throw new Error('A classified corpus and agreed themes are required.');
  if (!(alpha > 0 && alpha < 1)) throw new Error('Alpha must be between zero and one.');
  const allowed = new Set([...themes, NONE]);
  if (classified.some(r => !allowed.has(r.theme) || ['error','unmatched','empty'].includes(r.status))) throw new Error('Resolve missing, failed, or invalid classifications before estimating prevalence.');
  const entries = validatePeriods(periods), names = entries.map(e => e[0]);
  let invalidDates = 0, outsidePeriods = 0;
  const grouped = Object.fromEntries(names.map(n => [n, []]));
  for (const row of classified) {
    const d = String(row.date || '');
    if (!/^\d{4}-\d{2}-\d{2}$/.test(d) || !Number.isFinite(Date.parse(d)) || new Date(d).toISOString().slice(0,10) !== d) { invalidDates++; continue; }
    const period = entries.find(([, [s, e]]) => s <= d && d <= e);
    if (period) grouped[period[0]].push(row); else outsidePeriods++;
  }
  if (invalidDates) throw new Error(`${invalidDates} documents have missing or invalid dates. Use YYYY-MM-DD.`);
  if (names.some(n => !grouped[n].length)) throw new Error('At least one period has no documents. Adjust the ranges.');
  const pairs = names.flatMap((a, i) => names.slice(i + 1).map(b => [a, b]));
  const alphaAdj = alpha / (themes.length * pairs.length), prevRows = [], testRows = [];
  for (const theme of themes) {
    const counts = Object.fromEntries(names.map(n => [n, grouped[n].filter(r => r.theme === theme).length]));
    const row = {theme};
    for (const p of names) { row[`${p}_pct`] = 100 * counts[p] / grouped[p].length; row[`${p}_k`] = counts[p]; row[`${p}_n`] = grouped[p].length; }
    prevRows.push(row);
    for (const [a, b] of pairs) {
      const ka = counts[a], na = grouped[a].length, kb = counts[b], nb = grouped[b].length;
      const pa = ka / na, pb = kb / nb;
      // b minus a: a rise produces a positive z, matching the dissertation convention.
      const {z, p} = proportionsZTest(kb, nb, ka, na);
      const sparse = Math.min(ka, na-ka, kb, nb-kb) < 5;
      testRows.push({theme, comparison: `${a} vs ${b}`, period_a:a, k_a:ka, n_a:na, prop_a:pa, period_b:b, k_b:kb, n_b:nb, prop_b:pb,
        percentage_point_change:100*(pb-pa), pct_change:pa ? 100*(pb-pa)/pa : null, z, p,
        alpha_bonferroni:alphaAdj, significant_bonferroni:p !== null && p < alphaAdj, sparse_cells:sparse});
    }
  }
  return {prevRows, testRows, alphaAdj, periods:names, outsidePeriods, invalidDates, nDocuments:classified.length};
}

export async function sha256(value) {
  const bytes = typeof value === 'string' ? new TextEncoder().encode(value) : value;
  return [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map(v => v.toString(16).padStart(2,'0')).join('');
}
