/* The tutorial's live lab. Two exercises, both "commit before reveal":
   1. Name it yourself: type a name for a topic, then ask the live model 20
      times, then see the recorded 500-vote proposal and the researchers' theme.
   2. Code five: choose a theme for five first-term posts with the frozen
      codebook, then see what the live model chose for the same posts.
   Calls go to the site's existing public endpoint (/api/demo) with the two
   server-approved tasks: name a recorded topic, classify an archived post.
   Nothing you type is sent anywhere; only topic and post identifiers are. */

import { publicSession } from './live-session.js';

const $ = id => document.getElementById(id);
const el = (tag, props = {}, ...children) => {
  const node = Object.assign(document.createElement(tag), props);
  node.append(...children.filter(c => c !== null && c !== undefined));
  return node;
};
// Archive text sometimes carries doubled CSV quotes; tidy them for reading only.
const entities = { '&amp;': '&', '&lt;': '<', '&gt;': '>', '&quot;': '"', '&#39;': "'" };
const readable = text => text.replace(/&amp(?!;)/g, '&amp;').replace(/&(amp|lt|gt|quot|#39);/g, m => entities[m]).replace(/""/g, '"').replace(/^"+(?=\S)|(?<=\S)"+$/g, '').trim();
const normalise = label => label.trim().replace(/^["'“”]+|["'“”]+$/g, '').replace(/\.+$/, '').trim();

// Show a codebook entry as labelled lines, keeping the researchers' words.
const LABELS = ['Meaning', 'Include', 'Exclude', 'Examples and boundaries'];
function definitionBlock(text) {
  const block = el('div', { className: 'defn' });
  let current = null;
  for (const raw of text.split('\n')) {
    const line = raw.replace(/\s*\|\s*$/, '').trim();
    if (!line) continue;
    const label = LABELS.find(l => line.startsWith(l + ':'));
    if (label) {
      const rest = line.slice(label.length + 1).trim();
      if (label.startsWith('Examples')) {
        block.append(el('p', {}, el('b', { textContent: `${label}:` })));
        current = el('ul');
        if (rest) current.append(el('li', { textContent: rest.replace(/^\d+\.\s*/, '') }));
        block.append(current);
      } else {
        current = el('p', {}, el('b', { textContent: `${label}: ` }), rest);
        block.append(current);
      }
    } else if (current && current.tagName === 'UL') {
      current.append(el('li', { textContent: line.replace(/^\d+\.\s*/, '') }));
    } else block.append(el('p', { textContent: line }));
  }
  return block;
}

let tutorial, live, config;

async function loadData() {
  const [a, b] = await Promise.all([fetch('../data/trump/tutorial.json'), fetch('../data/trump/live-examples.json')]);
  if (!a.ok || !b.ok) throw new Error('Tutorial data could not be loaded.');
  [tutorial, live] = await Promise.all([a.json(), b.json()]);
  try {
    const response = await fetch('/api/config');
    config = response.ok ? await response.json() : { publicLive: false };
  } catch { config = { publicLive: false }; }
}

async function call(input) {
  await publicSession.ensure();
  const response = await fetch('/api/demo', {
    method: 'POST', credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', 'X-Request-ID': crypto.randomUUID() },
    body: JSON.stringify(input), signal: AbortSignal.timeout(60000),
  });
  const result = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(result.error || 'The request could not be completed.');
  return result;
}

// Run tasks with limited concurrency, reporting each result as it lands.
async function pool(items, limit, worker) {
  let next = 0;
  const runners = Array.from({ length: Math.min(limit, items.length) }, async () => {
    while (next < items.length) { const i = next++; await worker(items[i], i); }
  });
  await Promise.all(runners);
}

/* ------------------------------------------------------- name it yourself */
function initNaming() {
  const select = $('name-topic'), input = $('name-yours'), run = $('name-run'), state = $('name-state');
  const tally = $('name-tally'), reveal = $('name-reveal');
  const liveOn = Boolean(config.publicLive);
  for (const t of tutorial.topics) select.add(new Option(`Topic ${t.id} · ${t.words.slice(0, 3).join(', ')} · ${t.posts.toLocaleString()} posts`, String(t.id)));
  run.textContent = liveOn ? 'Ask the model 20 times' : 'Show the recorded answer';
  if (!liveOn) state.textContent = 'The live model is paused right now. You can still compare your name with the recorded 500 votes.';
  let busy = false;
  const topic = () => tutorial.topics.find(t => String(t.id) === select.value);
  const show = () => {
    const t = topic();
    $('name-words').textContent = `Top words: ${t.words.join(', ')}`;
    $('name-posts').replaceChildren(...t.examples.map(e => el('li', { textContent: readable(e.text) })));
    tally.replaceChildren(); reveal.hidden = true;
    if (liveOn) state.textContent = '';
  };
  const enable = () => { run.disabled = busy || normalise(input.value).length < 2; };
  select.addEventListener('change', () => { show(); enable(); });
  input.addEventListener('input', enable);
  input.addEventListener('keydown', e => { if (e.key === 'Enter' && !run.disabled) run.click(); });

  const drawTally = (counts, done, total) => {
    const sorted = [...counts.values()].sort((a, b) => b.n - a.n).slice(0, 6);
    tally.replaceChildren(...sorted.map(({ label, n }) => el('div', { className: 't' },
      el('span', { className: 'lbl', textContent: label, title: label }),
      el('span', { className: 'c', textContent: `${n}` }),
      el('span', { className: 'bar-v' }, el('i', { style: `width:${(n / total) * 100}%` })))));
    state.textContent = done < total ? `Asked ${done} of ${total} times…` : `The model's ${total} answers, most common first. ${counts.size} different wordings.`;
  };

  run.addEventListener('click', async () => {
    const t = topic(), yours = normalise(input.value);
    if (!t || yours.length < 2) return;
    busy = true; enable(); select.disabled = true; reveal.hidden = true; tally.replaceChildren();
    const counts = new Map();
    let done = 0, failure = null;
    if (liveOn) {
      const total = 20;
      state.textContent = 'Asking the model…';
      try {
        await pool([...Array(total).keys()], 4, async () => {
          if (failure) return;
          try {
            const result = await call({ task: 'name', topicId: String(t.id) });
            const label = normalise(result.text || '');
            const key = label.toLowerCase();
            if (label) counts.set(key, { label, n: (counts.get(key)?.n || 0) + 1 });
            done += 1; drawTally(counts, done, total);
          } catch (error) { failure = error; }
        });
      } finally { busy = false; select.disabled = false; enable(); }
      if (failure) state.replaceChildren(
        el('span', { className: 'err', textContent: `${failure.message} ` }),
        done ? `${done} answers arrived before the stop.` : '');
    } else { busy = false; select.disabled = false; enable(); }
    $('reveal-you').textContent = yours;
    $('reveal-model').textContent = `${t.model_name} (${t.model_votes} of ${t.model_total} votes)`;
    $('reveal-human').textContent = t.theme;
    reveal.hidden = false;
  });
  show(); enable();
}

/* ------------------------------------------------------------- code five */
function initCoding() {
  const list = $('code-posts'), run = $('code-run'), more = $('code-more'), state = $('code-state'), score = $('code-score');
  const liveOn = Boolean(config.publicLive);
  const options = [...tutorial.themes, tutorial.residual];
  const label = theme => tutorial.short_names[theme] || theme;
  const definition = theme => theme === tutorial.residual
    ? 'Use when nothing in the codebook closely fits the post.'
    : (tutorial.codebook.themes[theme] || '').trim();

  // The codebook panel.
  const book = $('code-book');
  for (const theme of tutorial.themes) book.append(el('dt', { textContent: theme }), el('dd', {}, definitionBlock(definition(theme))));
  book.append(el('dt', { textContent: 'Fits no theme' }), el('dd', { textContent: definition(tutorial.residual) }));
  book.append(el('dt', { textContent: 'When a post fits several themes' }), el('dd', { textContent: tutorial.codebook.decision_rule.trim() }));

  const used = new Set();
  let current = [];
  const pick = () => {
    const pool5 = live.examples.filter(e => !used.has(e.id) && e.text.replace(/https?:\/\/\S+/g, '').trim().length > 30);
    const chosen = [];
    while (chosen.length < 5 && pool5.length) chosen.push(pool5.splice(Math.floor(Math.random() * pool5.length), 1)[0]);
    chosen.forEach(e => used.add(e.id));
    return chosen;
  };
  const ready = () => { run.disabled = !current.length || current.some(c => !c.select.value) || !liveOn; };

  const deal = () => {
    score.hidden = true; more.hidden = true; state.textContent = liveOn ? '' : 'The live model is off right now. You can still code the five posts and compare your choices with the matrix above.';
    current = pick().map((example, i) => {
      const select = el('select');
      select.setAttribute('aria-label', `Theme for post ${i + 1}`);
      select.add(new Option('Choose a theme…', ''));
      options.forEach(theme => select.add(new Option(label(theme), theme)));
      select.addEventListener('change', ready);
      const answer = el('div', { className: 'answer' });
      const item = el('li', {},
        el('blockquote', { textContent: readable(example.text) }),
        el('p', { className: 'meta', textContent: `${example.date}${example.is_retweet === 't' ? ' · retweet' : ''}` }),
        select, answer);
      return { example, select, answer, item };
    });
    list.replaceChildren(...current.map(c => c.item));
    run.hidden = !liveOn; ready();
  };

  const showAnswer = (c, model) => {
    const mine = c.select.value, agree = mine === model;
    c.answer.replaceChildren(
      el('span', { className: agree ? 'match' : 'miss', textContent: agree ? `The model agrees: ${label(model)}` : `The model chose: ${label(model)}` }));
    if (!agree) {
      const details = el('details', {}, el('summary', { textContent: 'Compare the two definitions' }),
        el('h4', { textContent: `Your choice: ${label(mine)}` }), definitionBlock(definition(mine)),
        el('h4', { textContent: `The model's choice: ${label(model)}` }), definitionBlock(definition(model)));
      c.answer.append(details);
    }
    return agree;
  };

  run.addEventListener('click', async () => {
    run.disabled = true; current.forEach(c => { c.select.disabled = true; });
    state.textContent = 'The model is coding the same five posts…';
    const results = new Array(current.length);
    let failure = null;
    await pool(current.map((c, i) => i), 3, async i => {
      if (failure) return;
      try { results[i] = (await call({ task: 'classify', exampleId: current[i].example.id })).text; }
      catch (error) { failure = error; }
    });
    // Reveal in order, a beat apart.
    let agreed = 0, shown = 0;
    for (let i = 0; i < current.length; i++) {
      if (!results[i]) continue;
      await new Promise(r => setTimeout(r, matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 280));
      if (showAnswer(current[i], results[i])) agreed += 1;
      shown += 1;
    }
    if (failure) {
      state.replaceChildren(el('span', { className: 'err', textContent: failure.message }));
      current.forEach((c, i) => { if (!results[i]) c.select.disabled = false; });
      run.disabled = false;
      if (!shown) return;
    } else state.textContent = '';
    let total = { agree: 0, posts: 0 };
    try { total = JSON.parse(localStorage.getItem('topicllm-code-five') || '{"agree":0,"posts":0}'); } catch {}
    total = { agree: total.agree + agreed, posts: total.posts + shown };
    try { localStorage.setItem('topicllm-code-five', JSON.stringify(total)); } catch {}
    const y = tutorial.yardstick;
    score.replaceChildren(
      el('div', { className: 'big', textContent: `You and the model agreed on ${agreed} of ${shown}.` }),
      el('p', { textContent: `Two trained coders agreed with each other on ${Math.round(y.human_agreement * 100)}% of ${y.sample} posts. The model matched their consensus ${Math.round(y.classifier_agreement * 100)}% of the time.` }),
      ...(total.posts > shown ? [el('p', { className: 'small', textContent: `Your running total in this browser: ${total.agree} of ${total.posts}.` })] : []));
    score.hidden = false; run.hidden = true; more.hidden = false;
  });
  more.addEventListener('click', () => { deal(); list.scrollIntoView({ behavior: 'smooth', block: 'start' }); });
  deal();
}

try {
  await loadData();
  initNaming();
  initCoding();
} catch (error) {
  for (const id of ['name-state', 'code-state']) { const node = $(id); if (node) node.textContent = 'The lab could not load. The rest of the tutorial still works.'; }
}
