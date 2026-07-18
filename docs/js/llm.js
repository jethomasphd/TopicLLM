/* llm.js — LLM access for Stages 2 & 4, entirely from the browser.
 *
 * Providers:
 *  - "openai":    any OpenAI-compatible /chat/completions endpoint
 *                 (api.openai.com, OpenRouter, Groq, local Ollama, …)
 *  - "anthropic": the Anthropic Messages API (browser access enabled via
 *                 the anthropic-dangerous-direct-browser-access header)
 *  - "mock":      a keyless demonstration stand-in (clearly labeled; it is
 *                 NOT a language model — it synthesizes labels from topic
 *                 words so the workflow can be exercised without cost)
 *
 * The API key is held in memory / localStorage on the user's machine and is
 * sent only to the endpoint the user configures. No server of ours exists.
 */

import { mulberry32, fnv1a, choice } from "./util.js";

export function createProvider(settings) {
  const { provider } = settings;
  if (provider === "mock") return mockProvider(settings);
  if (provider === "anthropic") return anthropicProvider(settings);
  return openaiProvider(settings);
}

/** Retry with exponential backoff (2, 4, 8, 16, 32 s) — max 5 retries,
 * matching the reference implementation. */
export async function callWithRetries(fn, maxRetries = 5, onRetry = null) {
  for (let attempt = 0; ; attempt++) {
    try {
      return await fn();
    } catch (err) {
      if (attempt >= maxRetries - 1) return "Error: Unable to generate response";
      const wait = 2 ** (attempt + 1) * 1000;
      if (onRetry) onRetry(err, attempt + 1, wait);
      await new Promise(r => setTimeout(r, wait));
    }
  }
}

/** Run async task factories with bounded concurrency; preserves order. */
export async function pool(taskFns, concurrency, onProgress) {
  const results = new Array(taskFns.length);
  let next = 0, done = 0;
  async function workerLoop() {
    while (next < taskFns.length) {
      const i = next++;
      results[i] = await taskFns[i]();
      done++;
      if (onProgress) onProgress(done, taskFns.length, results[i], i);
    }
  }
  const workers = Array.from({ length: Math.max(1, concurrency) }, workerLoop);
  await Promise.all(workers);
  return results;
}

/* ------------------------- real providers -------------------------------- */

function openaiProvider({ apiKey, baseUrl, model }) {
  const url = (baseUrl || "https://api.openai.com/v1").replace(/\/+$/, "") + "/chat/completions";
  return {
    label: `${model} (OpenAI-compatible)`,
    model,
    async chat(system, user, { temperature, maxTokens }) {
      const resp = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${apiKey}` },
        body: JSON.stringify({
          model,
          messages: [{ role: "system", content: system }, { role: "user", content: user }],
          temperature, max_tokens: maxTokens, n: 1,
        }),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${(await resp.text()).slice(0, 200)}`);
      const data = await resp.json();
      return (data.choices?.[0]?.message?.content || "").trim();
    },
  };
}

function anthropicProvider({ apiKey, model }) {
  return {
    label: `${model} (Anthropic)`,
    model,
    async chat(system, user, { temperature, maxTokens }) {
      const resp = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-api-key": apiKey,
          "anthropic-version": "2023-06-01",
          "anthropic-dangerous-direct-browser-access": "true",
        },
        body: JSON.stringify({
          model, system, max_tokens: maxTokens, temperature,
          messages: [{ role: "user", content: user }],
        }),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${(await resp.text()).slice(0, 200)}`);
      const data = await resp.json();
      return (data.content?.[0]?.text || "").trim();
    },
  };
}

/* --------------------------- demo mock ----------------------------------- */

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
