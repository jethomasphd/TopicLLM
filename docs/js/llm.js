/* Hosted OpenAI gateway plus an explicitly labeled teaching mock. */
import { mulberry32, fnv1a, choice } from "./util.js";
export function createProvider(settings) {
  if (settings.provider === "mock") return mockProvider(settings);
  if (settings.provider !== "hosted") throw new Error("Choose Hosted OpenAI or the teaching mock.");
  const records = [];
  return {
    model: settings.model || "hosted-openai", label: "OpenAI via the research gateway", records,
    async chat(system, user, options) {
      const response = await fetch("/api/llm", {method:"POST", signal:settings.signal,
        headers:{"Content-Type":"application/json", Authorization:`Bearer ${settings.apiKey}`},
        body:JSON.stringify(options.taskData)});
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        const error = new Error(data.error || `LLM request failed (${response.status}).`);
        error.retryable = data.retryable !== false && (response.status >= 500 || response.status === 429);
        error.retryAfterMs = Math.min(60000, Math.max(0, Number(response.headers.get('Retry-After')) || 0) * 1000);
        error.signal = settings.signal;
        throw error;
      }
      const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(JSON.stringify(options.taskData)));
      const input_sha256 = [...new Uint8Array(digest)].map(n=>n.toString(16).padStart(2,'0')).join('');
      records.push({task:options.taskData.task, input_sha256, raw_response:data.text, received_at:new Date().toISOString(), model:data.model, request_id:data.request_id, usage:data.usage,
        system_fingerprint:data.system_fingerprint, temperature:data.temperature, max_tokens:data.max_tokens});
      return data.text;
    }
  };
}
export async function callWithRetries(fn, maxRetries=5, onRetry=null) {
  for (let attempt=0; ; attempt++) {
    try { return await fn(); }
    catch (error) {
      if (error.name === "AbortError" || error.retryable === false || attempt >= maxRetries-1) throw error;
      const wait=Math.max(error.retryAfterMs || 0, 2**(attempt+1)*1000);
      onRetry?.(error,attempt+1,wait);
      await new Promise((resolve,reject) => {
        const stop=()=>{clearTimeout(timer);reject(new DOMException('Run stopped','AbortError'));};
        const timer=setTimeout(()=>{error.signal?.removeEventListener('abort',stop);resolve();},wait);
        if(error.signal?.aborted) stop(); else error.signal?.addEventListener('abort',stop,{once:true});
      });
    }
  }
}
export async function pool(tasks, concurrency, progress) {
  const results=new Array(tasks.length); let next=0, done=0, failure=null;
  async function loop() {
    while (next<tasks.length && !failure) {
      const i=next++;
      try { results[i]=await tasks[i](); done++; progress?.(done,tasks.length,results[i],i); }
      catch (error) { failure=error; }
    }
  }
  await Promise.all(Array.from({length:Math.max(1,Math.min(concurrency,8))},loop));
  if (failure) throw failure;
  return results;
}
const TITLE = w => w.charAt(0).toUpperCase() + w.slice(1);

function mockProvider({ mockHints }) {
  // mockHints: { themes: {name: [keywords]}, noneLabel } — supplied for
  // classification calls; naming needs nothing beyond the prompt itself.
  let counter = 0;
  return {
    label: "demo mock (not a real LLM)",
    model: "mock-demo",
    async chat(system, user) {
      const rng = mulberry32(fnv1a(user) ^ (counter++ * 2654435761));
      await new Promise(r => setTimeout(r, 2)); // simulate latency
      if (/naming topics/i.test(system)) {
        const m = user.match(/:\s*([^.]*?)\.\s*Please provide/);
        const words = (m ? m[1] : user).split(",").map(w => w.trim()).filter(Boolean);
        const [a, b, c] = [words[0] || "topic", words[1] || "theme", words[2] || "content"];
        const roll = rng();
        if (roll < 0.55) return `${TITLE(a)} ${TITLE(b)}`;
        if (roll < 0.75) return `${TITLE(a)} ${TITLE(b)} ${TITLE(c)}`;
        if (roll < 0.9) return `${TITLE(a)} and ${TITLE(b)}`;
        return `${TITLE(b)} ${TITLE(a)}`;
      }
      // classification: score themes by keyword hits in the text
      const textMatch = user.match(/Text:\s*([\s\S]*?)\.\s*Respond with/);
      const text = (textMatch ? textMatch[1] : user).toLowerCase();
      const tokens = new Set(text.replace(/[^a-z]/g, " ").split(/\s+/).filter(Boolean));
      let bestTheme = null, bestScore = 0;
      for (const [theme, keywords] of Object.entries(mockHints?.themes || {})) {
        let score = 0;
        for (const k of keywords) {
          for (const t of tokens) {
            if (t === k || (t.length >= 5 && k.length >= 5 && t.slice(0, 5) === k.slice(0, 5))) { score++; break; }
          }
        }
        if (score > bestScore) { bestScore = score; bestTheme = theme; }
      }
      const none = mockHints?.noneLabel || "The text does not fit into any of these themes";
      if (rng() < 0.04) { // simulate imperfection so agreement is not 100%
        const names = Object.keys(mockHints?.themes || {});
        return names.length ? choice(names, rng) : none;
      }
      return bestScore >= 2 && bestTheme ? bestTheme : none;
    },
  };
}
