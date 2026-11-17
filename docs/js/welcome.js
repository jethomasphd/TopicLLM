import {welcomeVersion, welcomeTitle, welcomeLetter} from './welcome-content.js';

const storageKey = 'topicllm-welcome-acknowledged';
let acknowledged = false;
try { acknowledged = localStorage.getItem(storageKey) === welcomeVersion; } catch {}

const dialog = document.createElement('dialog');
dialog.className = 'welcome-dialog';
dialog.id = 'author-welcome';
dialog.setAttribute('aria-labelledby', 'welcome-title');
dialog.innerHTML = `
 <header class="welcome-header">
  <div class="welcome-byline"><svg viewBox="0 0 64 64" aria-hidden="true"><use href="/assets/topicllm-mark.svg#mark"></use></svg><span>A letter from the creator</span></div>
  <h2 id="welcome-title" tabindex="-1">${welcomeTitle}</h2>
  <p>Explore the evidence. Run with an agent. Review as a researcher.</p>
  <button class="welcome-close" type="button" aria-label="Close author’s welcome" hidden>×</button>
 </header>
 <div class="welcome-scroll" tabindex="0" role="region" aria-label="Letter from Jacob E. Thomas"><article class="welcome-letter">${welcomeLetter}</article></div>
 <form class="welcome-footer">
  <label class="welcome-check"><input type="checkbox" required><span>I understand: TopicLLM is a research starting point. The demo illustrates the method; researchers remain responsible for interpretation and validation.</span></label>
  <div class="welcome-actions"><span>Remembered only in this browser. Reopen from “Author’s welcome.”</span><button type="submit" class="welcome-enter" disabled>Enter TopicLLM <span aria-hidden="true">→</span></button></div>
 </form>`;
document.body.append(dialog);
const checkbox = dialog.querySelector('input');
const enter = dialog.querySelector('.welcome-enter');
const close = dialog.querySelector('.welcome-close');
let previousFocus;

function openWelcome() {
 if (dialog.open) return;
 previousFocus = document.activeElement;
 checkbox.checked = acknowledged;
 enter.disabled = !acknowledged;
 enter.innerHTML = acknowledged ? 'Return to the site <span aria-hidden="true">→</span>' : 'Enter TopicLLM <span aria-hidden="true">→</span>';
 close.hidden = !acknowledged;
 dialog.setAttribute('closedby', acknowledged ? 'closerequest' : 'none');
 document.documentElement.classList.add('welcome-open');
 dialog.showModal();
 dialog.querySelector('.welcome-scroll').scrollTop = 0;
 dialog.querySelector('#welcome-title').focus({preventScroll:true});
}
function closeWelcome() { if (acknowledged) dialog.close(); }
checkbox.addEventListener('change', () => { enter.disabled = !checkbox.checked; });
dialog.querySelector('form').addEventListener('submit', event => {
 event.preventDefault();
 if (!checkbox.checked) return;
 acknowledged = true;
 try { localStorage.setItem(storageKey, welcomeVersion); } catch {}
 dialog.close();
});
dialog.addEventListener('cancel', event => { if (!acknowledged) event.preventDefault(); });
dialog.addEventListener('keydown', event => {
 if (event.key === 'Escape' && !acknowledged) { event.preventDefault(); event.stopPropagation(); }
 if (event.key === 'Tab') {
  const stops = [...dialog.querySelectorAll('a[href],button,input,[tabindex="0"]')]
   .filter(element => !element.disabled && !element.hidden && element.getClientRects().length);
  const first = stops[0], last = stops.at(-1), current = document.activeElement;
  if (event.shiftKey && (current === first || !stops.includes(current))) {
   event.preventDefault(); last?.focus();
  } else if (!event.shiftKey && (current === last || !stops.includes(current))) {
   event.preventDefault(); first?.focus();
  }
 }
});
dialog.addEventListener('close', () => {
 // Some embedded browsers dismiss a native dialog without a cancelable event.
 if (!acknowledged) { openWelcome(); return; }
 document.documentElement.classList.remove('welcome-open');
 if (previousFocus && previousFocus !== document.body) previousFocus.focus({preventScroll:true});
 else {
  const heading = document.querySelector('main h1, .page h1');
  if (heading) { heading.tabIndex = -1; heading.focus({preventScroll:true}); }
 }
});
close.addEventListener('click', closeWelcome);
document.addEventListener('click', event => {
 const trigger = event.target.closest('[data-open-welcome]');
 if (trigger) { event.preventDefault(); openWelcome(); }
});
if (!acknowledged) openWelcome();
