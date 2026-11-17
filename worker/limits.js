// One definition for enforcement and the public UI. Monetary limits are UTC windows.
export function publicLimits(env={}) {
  const positive=(key,fallback)=>{const n=Number(env[key]??fallback);return Number.isSafeInteger(n)&&n>0?n:0;};
  return {sessionCallsPerDay:positive('DEMO_SESSION_CALLS',200),ipCallsPerDay:positive('DEMO_IP_CALLS',600),
    siteCallsPerDay:positive('DEMO_SITE_CALLS',20000),concurrentCalls:positive('DEMO_CONCURRENT_CALLS',8),
    dailyUsd:Number(env.DEMO_DAILY_USD??20),monthlyUsd:Number(env.DEMO_MONTHLY_USD??620)};
}
