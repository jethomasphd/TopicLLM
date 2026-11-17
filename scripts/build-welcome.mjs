import {readFile, writeFile, mkdir} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
import {resolve} from 'node:path';
import {welcomeTitle, welcomeLetter} from '../docs/js/welcome-content.js';

const root = new URL('../', import.meta.url);
export async function welcomePage() {
 const guide = await readFile(new URL('docs/guide/index.html', root), 'utf8');
 const shell = guide.slice(0, guide.indexOf('<main'))
  .replace('Research guide — TopicLLM', 'A letter from the creator — TopicLLM')
  .replace('Ask the TopicLLM guide about the research, methodology, original Study 1 demonstration and reproducible Python workflow.', 'Why TopicLLM exists, how humans and agents work together, and an invitation from Jacob E. Thomas to test and extend the method.');
 return `${shell}<main class="reproduce welcome-page"><p class="eyebrow">A letter from the creator</p><h1>${welcomeTitle}</h1><p class="lede">Explore the evidence. Run with an agent. Review as a researcher.</p><article class="welcome-letter">${welcomeLetter}</article><p class="welcome-page-next"><a class="btn primary" href="../app/">Explore the demonstration →</a> <a class="btn" href="../reproduce/">Fork + run →</a></p></main></body></html>\n`;
}
if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
 await mkdir(new URL('docs/welcome/', root), {recursive:true});
 await writeFile(new URL('docs/welcome/index.html', root), await welcomePage());
 console.log('Built the permanent welcome page from the shared author letter.');
}
