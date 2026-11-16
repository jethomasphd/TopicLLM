/* Same-origin OpenAI gateway. Provider credentials never reach the browser. */
const MAX_BODY = 24000;
const json = (body, status = 200, extra = {}) => Response.json(body, {status, headers:{'Cache-Control':'no-store','X-Content-Type-Options':'nosniff', ...extra}});
const textField = (value, max) => typeof value === 'string' && value.trim().length > 0 && value.length <= max;

export function validateCall(data) {
  if (!data || !['name','classify'].includes(data.task)) throw new Error('Choose a supported research task.');
  if (data.task === 'name') {
    if (!textField(data.words, 1200) || !textField(data.domain, 400)) throw new Error('Topic words or domain context are missing or too long.');
    return {max_tokens:15, system:'You are an expert at naming topics.', user:`The following words represent a topic derived from ${data.domain}: ${data.words}. Please provide a concise, meaningful topic name that clearly summarizes these words. `};
  }
  if (!textField(data.text, 8000) || !Array.isArray(data.themes) || data.themes.length < 1 || data.themes.length > 25 || data.themes.some(t => !textField(t, 150)) || new Set(data.themes).size !== data.themes.length) throw new Error('Provide text and 1–25 unique theme names.');
  const options = [...data.themes, 'The text does not fit into any of these themes'];
  return {max_tokens:120, system:'You are an expert at classifying text into themes.', user:`Classify the following text into one of the following ${options.length} themes: ${options.map((v,i) => `${i+1}. ${v}`).join(', ')}.Text: ${data.text}.Respond with verbatim classification using only the specified ${options.length} options.`};
}

async function authorized(request, env) {
  const offered = request.headers.get('Authorization') || '';
  const expected = `Bearer ${env.RESEARCH_ACCESS_TOKEN}`;
  const digest = async s => new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s)));
  const [a,b] = await Promise.all([digest(offered),digest(expected)]);
  return a.reduce((diff, value, i) => diff | (value ^ b[i]), 0) === 0;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (!url.pathname.startsWith('/api/')) return env.ASSETS.fetch(request);
    const ready = !!(env.OPENAI_API_KEY && env.RESEARCH_ACCESS_TOKEN && env.OPENAI_MODEL && env.RATE_LIMITER);
    if (url.pathname === '/api/config' && request.method === 'GET') return json({ready, provider:'openai', model:env.OPENAI_MODEL || null, access:'research-token', maxTextLength:8000});
    if (url.pathname !== '/api/llm') return json({error:'Not found.'},404);
    if (request.method !== 'POST') return json({error:'Use POST.'},405, {'Allow':'POST'});
    if (!ready) return json({error:'Hosted LLM access has not been configured. The synthetic walkthrough remains available.'},503);
    const origin = request.headers.get('Origin');
    if (origin && origin !== url.origin) return json({error:'Cross-origin calls are not allowed.'},403);
    if (!await authorized(request,env)) return json({error:'Enter the research access code supplied by the site operator.'},401);
    const limit = await env.RATE_LIMITER.limit({key:`research:${request.headers.get('CF-Connecting-IP') || 'unknown'}`});
    if (!limit.success) return json({error:'Request rate exceeded. Wait one minute and retry.'},429, {'Retry-After':'60'});
    if (!request.headers.get('Content-Type')?.toLowerCase().startsWith('application/json')) return json({error:'Use application/json.'},415);
    if (Number(request.headers.get('Content-Length')) > MAX_BODY) return json({error:'Request too large.'},413);
    let call;
    try {
      // Stream limit also covers requests without a Content-Length header.
      const reader = request.body?.getReader();
      if (!reader) return json({error:'Request body is required.'},400);
      let size = 0; const parts = [];
      while (true) { const {done,value} = await reader.read(); if (done) break; size += value.byteLength; if (size > MAX_BODY) { await reader.cancel(); return json({error:'Request too large.'},413); } parts.push(value); }
      const body = new Uint8Array(size); let offset = 0; for (const part of parts) { body.set(part,offset); offset += part.length; }
      call = validateCall(JSON.parse(new TextDecoder().decode(body)));
    } catch (error) { return json({error:error instanceof SyntaxError ? 'Malformed JSON.' : error.message},400); }
    try {
      const response = await fetch('https://api.openai.com/v1/chat/completions', {
        method:'POST', signal:AbortSignal.timeout(45000),
        headers:{'Content-Type':'application/json', Authorization:`Bearer ${env.OPENAI_API_KEY}`},
        body:JSON.stringify({model:env.OPENAI_MODEL, messages:[{role:'system',content:call.system},{role:'user',content:call.user}], temperature:.5, max_tokens:call.max_tokens, n:1, store:false})
      });
      if (!response.ok) {
        // Expose only allowlisted operational codes, never raw provider messages.
        const failure = await response.json().catch(() => ({}));
        const quotaMessages = {
          insufficient_quota:'OpenAI API quota is unavailable. The site operator must check API credits and project limits before retrying.',
          credit_balance_exhausted:'OpenAI API credits are exhausted. The site operator must add credits before retrying.',
          organization_usage_limit_exceeded:'The OpenAI organization usage limit was reached. The site operator must review its approved limit.',
          organization_spend_limit_exceeded:'The OpenAI organization spending limit was reached. The site operator must review that limit.',
          project_spend_limit_exceeded:'The OpenAI project spending limit was reached. The site operator must review that limit.'
        };
        const code = Object.hasOwn(quotaMessages, failure.error?.code) ? failure.error.code : failure.error?.type === 'insufficient_quota' ? 'insufficient_quota' : null;
        if (response.status === 429 && code) return json({error:quotaMessages[code], code, retryable:false, request_id:response.headers.get('x-request-id')},429);
        const retryAfter = Number(response.headers.get('Retry-After'));
        const headers = retryAfter > 0 && Number.isFinite(retryAfter) ? {'Retry-After':String(Math.min(60, Math.ceil(retryAfter)))} : {};
        return json({error:response.status === 429 ? 'OpenAI rate limit reached. Wait and retry.' : 'OpenAI did not complete the request. No classification was recorded.', retryable:response.status === 429 || response.status >= 500, request_id:response.headers.get('x-request-id')},response.status === 429 ? 429 : 502,headers);
      }
      const data = await response.json(), choice = data.choices?.[0], content = choice?.message?.content;
      if (!content?.trim() || choice.finish_reason !== 'stop') return json({error:'OpenAI returned an empty or incomplete response. No label was recorded.'},502);
      return json({text:content.trim(), model:data.model, system_fingerprint:data.system_fingerprint || null, request_id:response.headers.get('x-request-id'), usage:data.usage || null, temperature:.5, max_tokens:call.max_tokens});
    } catch { return json({error:'The LLM service timed out or could not be reached. Retry this step.'},504); }
  }
};
