import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile, access} from 'node:fs/promises';

const read = path => readFile(new URL(`../${path}`, import.meta.url), 'utf8');
const pages = ['docs/index.html', 'docs/tutorial/index.html', 'docs/use/index.html', 'docs/research/index.html', 'docs/paper/index.html', 'docs/privacy/index.html', 'docs/studies/1/index.html', 'docs/studies/2/index.html'];
const pct = x => `${Math.round(x * 100)}%`;

test('the tutorial, paper and README carry the same headline numbers', async () => {
  const data = JSON.parse(await read('docs/data/trump/campaign/human_sample_prevalence.json'));
  const head = data.headline;
  const expected = [
    pct(head.fits_a_campaign_theme.share),                                   // 84%
    `${Math.round(head.fits_a_campaign_theme.wilson_95[0] * 100)}–${Math.round(head.fits_a_campaign_theme.wilson_95[1] * 100)}%`, // 79–88%
    pct(data.classifier_agreement),                                         // 70%
    pct(data.human_coder_agreement),                                        // 68%
  ];
  for (const file of ['docs/tutorial/index.html', 'docs/paper/index.html', 'README.md']) {
    const text = await read(file);
    for (const value of expected) assert.ok(text.includes(value), `${file} should state ${value}`);
  }
  const home = await read('docs/index.html');
  assert.match(home, /16%.*40%/s, 'home page states the residual comparison');
  assert.equal(pct(head.human_residual_share), '16%');
  assert.equal(pct(head.classifier_residual_share), '40%');
});

test('classifier shares are always labelled as an unvalidated teaching demonstration', async () => {
  for (const file of ['docs/tutorial/index.html', 'docs/paper/index.html']) {
    const text = await read(file);
    assert.match(text, /teaching demonstration · model-assigned shares/, file);
    assert.doesNotMatch(text, /validated prevalence estimates? of/i, file);
  }
  const protocol = JSON.parse(await read('docs/protocol.json'));
  assert.equal(protocol.tutorial_finding.classifier.validated, false);
  assert.equal(protocol.tutorial_finding.classifier.gate_passed, false);
});

test('every page shares one navigation, and no page gates or pops up on arrival', async () => {
  for (const file of pages) {
    const html = await read(file);
    const nav = html.match(/<nav id="site-nav"[^>]*>(.*?)<\/nav>/s);
    assert.ok(nav, `${file} has the shared navigation`);
    assert.deepEqual([...nav[1].matchAll(/>([^<]+)<\/a>/g)].map(m => m[1]), ['Tutorial', 'Use it', 'Research', 'Paper'], file);
    assert.doesNotMatch(html, /welcome\.js|research companion|data-welcome/i, file);
  }
  assert.doesNotMatch(await read('docs/research/index.html'), /data-ask/, 'the research page stays quiet: no guide');
});

test('the software paper stays on the method and the tutorial', async () => {
  const html = await read('docs/paper/index.html');
  const article = html.match(/<article>(.*)<\/article>/s)[1].replace(/<[^>]+>/g, ' ');
  assert.doesNotMatch(article, /alcohol|covid/i);
  assert.match(article, /not been independently validated/);
  assert.match(html, /id="limits"/);
});

test('every figure the pages use exists, with a phone-width version where offered', async () => {
  for (const file of pages.concat('README.md')) {
    const html = await read(file);
    for (const [, src] of html.matchAll(/(?:src|srcset)="([^"]*figures\/[^"]+\.svg)"/g)) {
      const path = file === 'README.md' ? src : new URL(src, new URL(`../${file}`, import.meta.url)).pathname.split('/TopicLLM/')[1] || src;
      await access(new URL(src, new URL(`../${file}`, import.meta.url)));
      assert.ok(path);
    }
  }
});
