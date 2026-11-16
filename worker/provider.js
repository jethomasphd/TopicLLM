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

export async function sendOpenAI(call, env) {
    try {
      const response = await fetch('https://api.openai.com/v1/chat/completions', {
        method:'POST', signal:AbortSignal.timeout(45000),
        headers:{'Content-Type':'application/json', Authorization:`Bearer ${env.OPENAI_API_KEY}`},
        body:JSON.stringify({model:env.OPENAI_MODEL, messages:[{role:'system',content:call.system},{role:'user',content:call.user}], temperature:.5, max_tokens:call.max_tokens, n:1, store:false,...(call.response_format?{response_format:call.response_format}:{})})
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
