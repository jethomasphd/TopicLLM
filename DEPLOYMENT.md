# Operate TopicLLM on Cloudflare

## Conversational guide

`/api/guide` answers bounded questions about the public dissertation and software. It shares the existing Durable Object, daily/monthly OpenAI budget, session/IP caps, concurrency limit and same-origin cookie with `/api/demo`. `GUIDE_ENABLED=false` pauses guide answers; `LIVE_DEMO_ENABLED=false` pauses all public model calls. The operator research route remains disabled. The static welcome and page orientation do not call OpenAI.

The guide uses the configured `gpt-4o-2024-08-06`, `store:false`, at most 1,600 output tokens, and the same conservative $2.50/million input and $10/million output accounting as the examples. It requests answers under 180 words, leaving room for the JSON structure and source IDs. Questions are limited to 1,200 characters and recent history to three exchanges and 9,000 characters. The response must pass JSON and source-ID checks. Source links are selected only from server-provided public references; the browser renders answer text without HTML interpretation. A deliberately resubmitted question can request a fresh answer after a confirmed rejected completion; uncertain network retries preserve their operation ID. Every new call remains subject to the same public caps.

Maintain `docs/guide/knowledge.md` as the high-level briefing. `worker/guide-sources.json` contains that briefing plus page-level dissertation and repository excerpts. Rebuild after any indexed source changes with `python -m pip install pypdf==6.21.4` and `python scripts/build-guide.py`; tests verify the source hashes. Retrieval is lexical and does not guarantee the most relevant passage for every phrasing. The guide cannot execute analyses, browse, access private records, or approve research. Validate substantive answers against cited sources.

Conversation history lives only in the current page's memory. The server keeps keyed request fingerprints and short response receipts for safe retries, expiring after 30 minutes, plus aggregate quota counters. Responses may reflect visitor questions. Do not log raw request bodies. OpenAI processing and retention are separate from application retention. The data-handling page discloses transmission before a question is sent.

The website at https://topicllm.dev is a visual demonstration with bounded public Trump examples. Researchers run their corpus in a fork or installed Python environment with their own approved credentials. One Cloudflare Worker serves the static site and same-origin API. The owner registered topicllm.dev in Cloudflare; both apex and www are attached to this Worker.

## Build a complete release

Use Node 22+, pnpm 11+, and Python 3.11+. From the repository root:

```sh
pnpm install --frozen-lockfile
python -m pip install ".[dev,docs]"
node scripts/build-welcome.mjs
python scripts/build-campaign-evidence.py
python scripts/build-guide.py
python scripts/render-methods.py
python -m pytest dtm_pipeline/tests -q
python -m build --wheel --outdir dist_wheels
python scripts/package-release.py
pnpm check
python scripts/check-publication-privacy.py
python scripts/check-published-metrics.py
pnpm exec wrangler deploy --dry-run
pnpm exec wrangler deploy
```

The `docs` extra pins the tools used to rebuild the guide and working-manuscript PDF. Inspect the rendered pages in `build-qa/methods_pdf_qa/` after manuscript changes; generation alone is not a layout check. Windows uses its installed Times and Arial fonts, with standard PDF fonts as the fallback on other systems. This can change pagination without changing the scientific text.

Keep exactly one wheel for the version declared in `pyproject.toml`; older versions are ignored. The packager includes source, selected public Trump data and licenses, excludes private runs and credentials, and writes the served wheel's download hash. Full repository downloads use GitHub's current-main archive; record its commit for an analysis. The locally generated source ZIP is excluded from static hosting because accumulated research evidence can exceed Cloudflare's [25 MiB per-file limit](https://developers.cloudflare.com/workers/platform/limits/).

The build copies `docs`, PDF.js and unchanged archival sources into `dist`; it verifies all ten protected source hashes. Publish the built assets, not raw `docs`. CI installs the wheel outside the checkout and runs the offline quickcheck on Windows/Ubuntu and Python 3.11/3.12. This lightweight matrix is not a full ML numerical-equivalence test.

## Secrets and endpoints

Authentication and secrets are configured for the existing deployment. For a new deployment, use Wrangler's private prompts:

```sh
pnpm exec wrangler login
pnpm exec wrangler secret put OPENAI_API_KEY
pnpm exec wrangler secret put RESEARCH_ACCESS_TOKEN
```

Never put secrets in source, chat, command arguments, browser storage or screenshots. The high-entropy research token signs sessions and authorizes operator status. It is never issued to visitors. Rotating it invalidates sessions. `/api/llm` carries authenticated research requests, including the exact frozen codebook prompt, only during explicitly budgeted execution. It is paused at human research gates and outside active runs. Visitors execute their own research in their own environment.

| Route | Purpose |
|---|---|
| `GET /api/config` | Configuration and live-example availability |
| `GET /api/health` | Rate-limited configuration/storage health |
| `GET /api/session` | Signed one-day secure HttpOnly session cookie |
| `POST /api/demo` | Same-origin, session-bound approved public Trump example IDs |
| `GET /api/admin/status` | Bearer-token-protected aggregate counters |
| `POST /api/llm` | Private budgeted research; paused at human gates and outside active runs |

The model is pinned to `gpt-4o-2024-08-06`; this is not asserted to be the dissertation's exact snapshot. Changing it requires reviewing prompts, token bounds, prices, validation and tests. Calls use `store:false`, which does not mean zero provider retention.

## Enforced allowances

The owner approved **$20 per UTC day and $620 per UTC calendar month** shared by public examples and the guide.

One globally named SQLite-backed Durable Object serializes reservations before provider calls. It enforces spending, 200 calls per session per day, 600 per daily hashed network address, 20,000 public calls per day and eight concurrent public calls. Per-location rate limiting adds an abuse control; the durable global ledger is the spending authority. Anonymous sessions are not verified people; shared networks may share limits.

Reservations use integer nano-dollars, a conservative UTF-8 input bound and the full output-token cap. Returned usage settles calls at $2.50 per million input tokens and $10 per million output tokens without caching discounts (verified 16 November 2026). Unknown usage and failures retain the full reservation. Storage failure stops requests; failed settlement releases no label. A bound violation disables further calls for review. These estimates cover OpenAI token charges, not taxes or Cloudflare infrastructure charges, and are not an invoice.

Request IDs bind to task fingerprints. Repeating a completed operation within thirty minutes returns its response without another provider request; altered payloads are rejected. Explicit retries use distinct attempt IDs. Python derives IDs from the logical operation, prompt/settings fingerprint and attempt number. Resume uses its local durable cache. Only one process should own a run directory.

Operator research has separate daily/monthly caps, twelve concurrent calls and a nonresetting allowance keyed by `OPERATOR_RUN_ID` (default `v1`). The authorized campaign-to-presidency application uses `campaign-presidency-20261118` and a $150 cumulative ceiling, raised by explicit authorization for the demonstration-only continuation. Its completed conservative accounting is $112.4674175, separate from earlier engineering validation. The research route is now disabled. Its completed naming responses and abandoned attempts remain charged to that same run. Preserve the run ID when resuming after human review; a new ID requires a separately authorized research budget. Do not delete the ledger, rename the object or rotate run IDs to evade a ceiling. Keep `OPERATOR_LLM_ENABLED=false` at human gates and after execution.

## Check and operate

After deployment, run one naming and one classification example on the live tab. Inspect model, request ID and usage; download the record. Verify guided calculations, original chapter checksums, downloads and the reproduction guide. A controlled duplicate-ID smoke check should produce only one provider charge. Repeat these checks after changes to Worker code or bindings.

`/api/health` returns HTTP 200 when configuration and storage work. This does not mean every visitor or the site has remaining allowance. Privately set `TOPICLLM_RESEARCH_TOKEN` in your shell environment, then inspect aggregate counters:

```sh
node scripts/service-status.mjs
```

`charged` is nano-USD (divide by 1,000,000,000). `calls` includes reserved attempts; `success`, `errors` and `denied` describe completed calls, failures and refused reservations. Uncertain calls retain charges. Compare known usage with the OpenAI project when checking billing. Application observability is disabled and corpus text/credentials are not logged.

Billing failures stop without invented labels. Inspect billing privately. To pause public calls, set `LIVE_DEMO_ENABLED=false` in `wrangler.jsonc` and deploy; the walkthrough and downloads remain available. Keep the operator switch false. Do not bypass quotas for troubleshooting. After repairs, run a small public-example smoke check before reopening. Use Wrangler's deployment version rollback when appropriate, preserving the Durable Object binding, migration and ledger.

Public-example and guide response receipts expire after thirty minutes with scheduled cleanup. Session and keyed-IP counts use UTC daily windows; budget counters retain active windows. Infrastructure processing is separate. See the website's [data-handling page](https://topicllm.dev/privacy/).

## Primary domain

The primary address is https://topicllm.dev. `wrangler.jsonc` attaches both `topicllm.dev` and `www.topicllm.dev` as Worker Custom Domains. Cloudflare manages DNS and HTTPS certificates. Keep these routes in subsequent deployments.

Browser navigation on www and the earlier workers.dev address redirects permanently to the HTTPS apex, preserving path and query. Browsers retain fragments across that redirect. Legacy GitHub Pages HTML also redirects to the apex, preserving path, query and fragment. API requests remain on their original origin for existing clients; the website uses the apex's same-origin API and secure host-only session cookie. All hosts share the same Durable Object allowance, so the domain change does not reset spending limits.

The Worker runs before static assets to enforce host redirects. `pnpm dev` sets the local-only `CANONICAL_REDIRECTS=false` override because Wrangler maps a custom-domain request back onto localhost during preview. Production leaves redirects enabled. Local development and unrelated fork hosts are not redirected. A fork owner should replace the custom-domain routes and the explicit redirect host list with their own deployment settings.

Official references: [Durable Object storage and transactions](https://developers.cloudflare.com/durable-objects/api/sqlite-storage-api/), [static assets](https://developers.cloudflare.com/workers/static-assets/), [secrets](https://developers.cloudflare.com/workers/configuration/secrets/), [rate-limit semantics](https://developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/), [custom domains](https://developers.cloudflare.com/workers/configuration/routing/custom-domains/), [GPT-4o pricing and snapshots](https://developers.openai.com/api/docs/models/gpt-4o), [OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data).

## Legacy address

The legacy jethomasphd.github.io/TopicLLM address uses the redirect-only workflow `.github/workflows/retire-legacy-pages.yml`. It publishes only index/404 redirect pages, not a second data or model service. The primary site, API and downloadable release are on topicllm.dev. Retired dissertation-data paths return HTTP 410 at the Worker; historical source papers remain available.

Versioned Worker preview URLs are disabled (`preview_urls: false`) so retired deployments are not alternate public data endpoints.
