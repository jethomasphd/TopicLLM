# Deploy TopicLLM on Cloudflare

The current deployment is https://topicllm.jethomasphd.workers.dev. Cloudflare authentication and both server secrets are configured. The deployed gateway reports ready and rejects unauthenticated calls. A successful live OpenAI completion is still a release check; configuration readiness alone does not establish provider billing or model availability.

This release uses one Cloudflare Worker with static assets. The website and `/api/llm` share an origin. No domain purchase is needed to test on `workers.dev`; attach a custom domain after choosing and purchasing it.

## Prepare and test

Use Node 22 or newer and pnpm 11 or newer.

```sh
pnpm install --frozen-lockfile
pnpm check
pnpm exec wrangler deploy --dry-run
pnpm exec wrangler login
```

`pnpm build` copies `docs/` into `dist/`, adds the unmodified dissertation and archival supplements, and checks every protected source hash. Do not publish raw `docs/` directly: the built output includes the authoritative source PDF.

## Configure OpenAI

```sh
pnpm exec wrangler secret put OPENAI_API_KEY
pnpm exec wrangler secret put RESEARCH_ACCESS_TOKEN
```

Enter secrets only in Wrangler's private prompt. `OPENAI_API_KEY` stays on the server. `RESEARCH_ACCESS_TOKEN` is a separate, high-entropy access code issued by the operator for the initial controlled research deployment. The browser retains it in memory only. Rotate it if shared beyond the intended group. For a broad public paid service, replace the shared research code with per-user identity and quotas before enabling unrestricted access.

`OPENAI_MODEL` in `wrangler.jsonc` pins `gpt-4o-2024-08-06`. This is an available GPT-4o snapshot choice, **not a claim that the dissertation used this exact snapshot**. Verify project access with a small synthetic request, record the provider-returned model identifier, and change the configuration if this snapshot is unavailable to the deployment account.

The Worker enforces supported tasks, input lengths, output limits, same-origin browser calls, a research access code and 120 requests per minute per IP per Cloudflare location. Rate limits are approximate and are not a global spending cap. Configure the OpenAI project budget and operational monitoring. Stage 2's historical budget alone is 35,000 requests for seven topics; use a small vote count for the initial smoke test.

Billing and quota failures return an allowlisted operational code and stop automatic retries. Temporary rate limits retain bounded retry guidance. The gateway never forwards raw provider error messages.

`store:false` is sent on API calls. This is not a claim of zero provider retention; review the project's applicable OpenAI data controls before sending research data. The application does not log corpus text or credentials, and Worker observability is disabled by default.

## Deploy and verify

```sh
pnpm deploy
```

Open the returned URL. `/api/config` should report `ready:true` and the configured model after both secrets and the rate limiter are present. In the workbench choose Hosted OpenAI, enter the research access code and run a small synthetic naming/classification check. Confirm that errors do not generate labels and that exported metadata records the returned model. Then verify the unchanged dissertation readers and the complete synthetic walkthrough.

For local development, create an ignored `.dev.vars` file with the two secrets, run `pnpm dev`, and use only approved synthetic inputs. Do not put provider keys in HTML, JavaScript, Git, browser storage, or screenshots.

## Add a domain

After registering a domain and adding it to the Cloudflare account, add a Worker Custom Domain in the dashboard or add a `routes` entry with `custom_domain:true` to `wrangler.jsonc`. Keep the app and API on the same origin. Verify HTTPS, links, downloads and API access on the domain before retiring GitHub Pages. Configure the old GitHub Pages site to redirect only after the new domain works.

## Deployment boundaries

The Worker handles LLM calls; it does not run Python BERTopic. Browser discovery is a bounded approximation. Large or publication analyses use the Python pipeline in an appropriate compute environment. The seven-topic walkthrough uses assigned synthetic categories, not a concealed fixed-cluster fit.

Official references: [static assets](https://developers.cloudflare.com/workers/static-assets/), [routing and bindings](https://developers.cloudflare.com/workers/static-assets/binding/), [secrets](https://developers.cloudflare.com/workers/configuration/secrets/), [rate-limit semantics](https://developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/), [custom domains](https://developers.cloudflare.com/workers/configuration/routing/custom-domains/), [GPT-4o snapshots](https://developers.openai.com/api/docs/models/gpt-4o), [OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data).
