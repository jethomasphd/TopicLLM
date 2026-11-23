import test from 'node:test';
import assert from 'node:assert/strict';
import { createPublicSession } from '../docs/js/live-session.js';

test('concurrent lab and guide calls share one session handshake', async () => {
  let calls = 0, release;
  const session = createPublicSession(async () => {
    calls += 1;
    await new Promise(resolve => { release = resolve; });
    return Response.json({ ready: true });
  });
  const waiting = Array.from({ length: 20 }, () => session.ensure());
  assert.equal(calls, 1);
  release();
  await Promise.all(waiting);
  await session.ensure();
  assert.equal(calls, 1);
  session.invalidate();
  const renewed = session.ensure();
  assert.equal(calls, 2);
  release();
  await renewed;
});

test('failed session handshake stops callers and can recover without a stuck promise', async () => {
  let calls = 0;
  const session = createPublicSession(async () => ++calls === 1
    ? Response.json({ error: 'Please wait.' }, { status: 429 })
    : Response.json({ ready: true }));
  const failed = await Promise.allSettled([session.ensure(), session.ensure()]);
  assert.equal(calls, 1);
  assert.ok(failed.every(r => r.status === 'rejected' && r.reason.status === 429));
  await session.ensure();
  assert.equal(calls, 2);
});
