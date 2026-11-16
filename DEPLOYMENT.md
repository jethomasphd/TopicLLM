# Operate TopicLLM on Cloudflare

The website at https://topicllm.jethomasphd.workers.dev is a visual demonstration with fixed synthetic OpenAI examples. Researchers run their corpus in a fork or installed Python environment with their own approved credentials. One Cloudflare Worker serves the static site and same-origin API. A custom domain awaits the owner's choice and purchase.

## Build a complete release

Use Node 22+, pnpm 11+, and Python 3.11+. From the repository root:

```sh
pnpm install --frozen-lockfile
python -m pip install ".[dev]"
python -m pytest dtm_pipeline/tests -q
python -m build --wheel --outdir dist_wheels
python scripts/package-release.py
pnpm check
pnpm exec wrangler deploy --dry-run
pnpm exec wrangler deploy
```

Keep exactly one wheel in `dist_wheels`. The packager includes source, canonical synthetic data and licenses, excludes private runs and credentials, and writes download hashes. The build copies `docs`, PDF.js and unchanged archival sources into `dist`; it verifies all ten protected source hashes. Publish the built assets, not raw `docs`. CI installs the wheel outside the checkout and runs the offline quickcheck on Windows/Ubuntu and Python 3.11/3.12. This lightweight matrix is not a full ML numerical-equivalence test.

## Secrets and endpoints

Authentication and secrets are configured for the existing deployment. For a new deployment, use Wrangler's private prompts:

```sh
pnpm exec wrangler login
pnpm exec wrangler secret put OPENAI_API_KEY
pnpm exec wrangler secret put RESEARCH_ACCESS_TOKEN
```

Never put secrets in source, chat, command arguments, browser storage or screenshots. The high-entropy research token signs sessions and authorizes operator status. It is never issued to visitors. Rotating it invalidates sessions. `/api/llm` is a private validation route, paused after the acceptance run, not a public research backend.

| Route | Purpose |
|---|---|
| `GET /api/config` | Configuration and live-example availability |
| `GET /api/health` | Rate-limited configuration/storage health |
| `GET /api/session` | Signed one-day secure HttpOnly session cookie |
| `POST /api/demo` | Same-origin, session-bound fixed synthetic example IDs |
| `GET /api/admin/status` | Bearer-token-protected aggregate counters |
| `POST /api/llm` | Private validation; disabled in the public release |

The model is pinned to `gpt-4o-2024-08-06`; this is not asserted to be the dissertation's exact snapshot. Changing it requires reviewing prompts, token bounds, prices, validation and tests. Calls use `store:false`, which does not mean zero provider retention.

## Enforced allowances

The owner approved **$1 per UTC day and $5 per UTC calendar month** for public examples, separate from the **one-time $5 validation allowance**.

One globally named SQLite-backed Durable Object serializes reservations before provider calls. It enforces spending, ten calls per session per day, thirty per daily hashed network address, 1,000 public calls per day and four concurrent public calls. Per-location rate limiting adds an abuse control; the durable global ledger is the spending authority. Anonymous sessions are not verified people; shared networks may share limits.

Reservations use integer nano-dollars, a conservative UTF-8 input bound and the full output-token cap. Returned usage settles calls at $2.50 per million input tokens and $10 per million output tokens without caching discounts (verified 16 November 2026). Unknown usage and failures retain the full reservation. Storage failure stops requests; failed settlement releases no label. A bound violation disables further calls for review. These estimates cover OpenAI token charges, not taxes or Cloudflare infrastructure charges, and are not an invoice.

Request IDs bind to task fingerprints. Repeating a completed operation within thirty minutes returns its response without another provider request; altered payloads are rejected. Explicit retries use distinct attempt IDs. Python derives IDs from the logical operation, prompt/settings fingerprint and attempt number. Resume uses its local durable cache. Only one process should own a run directory.

Operator validation has separate daily/monthly caps, twelve concurrent calls and a nonresetting `operator:validation:v1` allowance. Do not delete the ledger or rename the object to evade a ceiling. Keep `OPERATOR_LLM_ENABLED=false` after validation.

## Check and operate

After deployment, run one naming and one classification example on the live tab. Inspect model, request ID and usage; download the record. Verify guided calculations, original chapter checksums, downloads and the reproduction guide. A controlled duplicate-ID smoke check should produce only one provider charge. Repeat these checks after changes to Worker code or bindings.

`/api/health` returns HTTP 200 when configuration and storage work. This does not mean every visitor or the site has remaining allowance. Privately set `TOPICLLM_RESEARCH_TOKEN` in your shell environment, then inspect aggregate counters:

```sh
node scripts/service-status.mjs
```

`charged` is nano-USD (divide by 1,000,000,000). `calls` includes reserved attempts; `success`, `errors` and `denied` describe completed calls, failures and refused reservations. Uncertain calls retain charges. Compare known usage with the OpenAI project when checking billing. Application observability is disabled and corpus text/credentials are not logged.

Billing failures stop without invented labels. Inspect billing privately. To pause public calls, set `LIVE_DEMO_ENABLED=false` in `wrangler.jsonc` and deploy; the walkthrough and downloads remain available. Keep the operator switch false. Do not bypass quotas for troubleshooting. After repairs, run a small synthetic smoke check before reopening. Use Wrangler's deployment version rollback when appropriate, preserving the Durable Object binding, migration and ledger.

Synthetic response receipts expire after thirty minutes with scheduled cleanup. Session and keyed-IP counts use UTC daily windows; budget counters retain active windows. Infrastructure processing is separate. See the website's [data-handling page](https://topicllm.jethomasphd.workers.dev/privacy/).

## Attach the chosen domain

Register the owner's chosen domain and add it to Cloudflare. Attach a Worker Custom Domain in the dashboard or add a `routes` entry with `custom_domain:true`. Keep website and API on one origin. Verify HTTPS, sessions, readers, downloads and live examples on the custom domain. The legacy GitHub Pages HTML redirects visitors to the working Cloudflare site, preserving path, query and fragment; update that fixed target when the custom domain is ready. No domain has been purchased by this project.

Official references: [Durable Object storage and transactions](https://developers.cloudflare.com/durable-objects/api/sqlite-storage-api/), [static assets](https://developers.cloudflare.com/workers/static-assets/), [secrets](https://developers.cloudflare.com/workers/configuration/secrets/), [rate-limit semantics](https://developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/), [custom domains](https://developers.cloudflare.com/workers/configuration/routing/custom-domains/), [GPT-4o pricing and snapshots](https://developers.openai.com/api/docs/models/gpt-4o), [OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data).
