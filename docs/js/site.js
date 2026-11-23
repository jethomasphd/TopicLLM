/* Shared page behavior: mobile menu, copy buttons, chart draw-in, and the
   scroll position markers for the tutorial rail and the paper's contents.
   No network calls and no stored data. */

const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

// Mobile menu.
const menu = document.querySelector('[data-menu]');
const nav = document.getElementById('site-nav');
if (menu && nav) {
  const set = open => { menu.setAttribute('aria-expanded', String(open)); nav.classList.toggle('open', open); };
  menu.addEventListener('click', () => set(menu.getAttribute('aria-expanded') !== 'true'));
  nav.addEventListener('click', event => { if (event.target.closest('a')) set(false); });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && nav.classList.contains('open')) { set(false); menu.focus(); }
  });
}

// Copy buttons: <button class="copy" data-copy="#target">.
$$('[data-copy]').forEach(button => button.addEventListener('click', async () => {
  const target = document.querySelector(button.dataset.copy);
  if (!target) return;
  const text = target.innerText.replace(/^Copy\s*/,'').trim();
  try { await navigator.clipboard.writeText(text); button.textContent = 'Copied'; }
  catch { button.textContent = 'Select and copy'; }
  setTimeout(() => { button.textContent = 'Copy'; }, 1800);
}));

// Charts draw once as they scroll into view.
const drawables = $$('.draw');
if ('IntersectionObserver' in window && drawables.length) {
  const seen = new IntersectionObserver(entries => entries.forEach(entry => {
    if (entry.isIntersecting) { entry.target.classList.add('in'); seen.unobserve(entry.target); }
  }), { rootMargin: '0px 0px -8% 0px' });
  drawables.forEach(el => seen.observe(el));
} else drawables.forEach(el => el.classList.add('in'));

// Mark the section in view for any list of in-page links: [data-spy] a[href^="#"].
$$('[data-spy]').forEach(list => {
  const links = $$('a[href^="#"]', list);
  const targets = links.map(a => document.getElementById(a.getAttribute('href').slice(1))).filter(Boolean);
  if (!targets.length || !('IntersectionObserver' in window)) return;
  const mark = id => {
    let passed = true;
    links.forEach(a => {
      const on = a.getAttribute('href') === '#' + id;
      a.classList.toggle('on', on);
      if (on) { a.setAttribute('aria-current', 'step'); passed = false; } else a.removeAttribute('aria-current');
      a.classList.toggle('done', passed && !on);
    });
  };
  const spy = new IntersectionObserver(entries => {
    const visible = entries.filter(e => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
    if (visible[0]) mark(visible[0].target.id);
  }, { rootMargin: '-30% 0px -60% 0px' });
  targets.forEach(t => spy.observe(t));
});
