/* stats.js — Stage 5 theme-prevalence statistics: two-proportion z-tests
 * (pooled, two-sided), matching statsmodels proportions_ztest defaults. */

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
  if (![k1,n1,k2,n2].every(Number.isFinite) || n1 <= 0 || n2 <= 0 || k1 < 0 || k2 < 0 || k1 > n1 || k2 > n2) throw new Error('Invalid binomial counts.');
  const p1 = k1 / n1, p2 = k2 / n2;
  const pooled = (k1 + k2) / (n1 + n2);
  const se = Math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2));
  if (se === 0) return { z: null, p: null };
  const z = (p1 - p2) / se;
  const p = Math.min(1, 2 * normalCDF(-Math.abs(z)));
  return { z, p };
}
