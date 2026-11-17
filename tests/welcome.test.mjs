import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {welcomePage} from '../scripts/build-welcome.mjs';
import {guideCall, retrieve} from '../worker/guide.js';

test('permanent author letter stays identical to the arrival dialog source', async () => {
 const page = await readFile(new URL('../docs/welcome/index.html', import.meta.url), 'utf8');
 assert.equal(page.replace(/\r\n/g,'\n'), (await welcomePage()).replace(/\r\n/g,'\n'));
});
test('guide supports the welcome page and retrieves the scientific status context', () => {
 const call = guideCall({page:'welcome',question:'Why did Jacob Thomas create TopicLLM at UT Austin?'});
 assert.ok(call.sources.some(s => s.id === 'welcome' && s.url === '/welcome/'));
 assert.ok(retrieve('dissertation committee independent scientific replication welcome', 8).some(s => s.url === '/welcome/'));
});
