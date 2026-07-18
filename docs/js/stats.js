/* stats.js — Stage 5 inference: two-proportion z-tests (pooled, two-sided),
 * matching statsmodels.stats.proportion.proportions_ztest defaults. */

/** Standard normal CDF via the Abramowitz–Stegun erf approximation. */
export function normalCDF(x) {
  const t = 1 / (1 + 0.2316419 * Math.abs(x));
  const d = 0.3989422804014327 * Math.exp(-x * x / 2);
  let p = d * t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))));
  if (x > 0) p = 1 - p;
  return p;
}

/** Two-proportion z-test. Returns { z, p } (two-sided, pooled variance). */
export function proportionsZTest(k1, n1, k2, n2) {
  if (!n1 || !n2) return { z: NaN, p: NaN };
  const p1 = k1 / n1, p2 = k2 / n2;
  const pooled = (k1 + k2) / (n1 + n2);
  const se = Math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2));
  if (se === 0) return { z: 0, p: 1 };
  const z = (p1 - p2) / se;
  const p = 2 * (1 - normalCDF(Math.abs(z)));
  return { z, p };
}
