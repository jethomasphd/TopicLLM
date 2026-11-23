// Share one session handshake across simultaneous lab and guide requests.
export function createPublicSession(fetcher = globalThis.fetch) {
  let ready = false, pending = null;
  return {
    async ensure() {
      if (ready) return;
      pending ??= (async () => {
        const response = await fetcher('/api/session', { credentials: 'same-origin' });
        if (!response.ok) {
          const body = await response.json().catch(() => ({}));
          throw Object.assign(new Error(body.error || 'The live model is unavailable right now.'), { status: response.status });
        }
        ready = true;
      })().finally(() => { pending = null; });
      return pending;
    },
    invalidate() { ready = false; },
  };
}

export const publicSession = createPublicSession();
