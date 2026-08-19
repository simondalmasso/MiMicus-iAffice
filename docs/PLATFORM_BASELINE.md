# Platform baseline

Retrieved/reverified: 2026-08-19 UTC. Sources are official Cloudflare/Notion documentation unless explicitly identified as npm package metadata.

| Surface | Free baseline used by AriaOS | Source |
|---|---|---|
| Workers | 100,000 requests/day; 10 ms CPU per HTTP invocation; max 5 Cron Triggers/account | https://developers.cloudflare.com/workers/platform/limits/ |
| Workflows | Free available; 100k requests/day shared with Workers; 10 ms CPU/invocation; 1 GB state; 3,000 steps/day; over-limit state operations fail | https://developers.cloudflare.com/workflows/reference/pricing/ ; https://developers.cloudflare.com/workflows/reference/limits/ |
| D1 | 5M rows read/day, 100k rows written/day, 5 GB/account; 500 MB/database | https://developers.cloudflare.com/d1/platform/pricing/ ; https://developers.cloudflare.com/d1/platform/limits/ |
| Queues | 10,000 operations/day Free; Free retention 24 h; consumer supports retry + DLQ | https://developers.cloudflare.com/queues/platform/pricing/ ; https://developers.cloudflare.com/queues/platform/limits/ ; https://developers.cloudflare.com/queues/configuration/dead-letter-queues/ |
| Durable Objects | Available on Workers Free with SQLite storage; Free over-limit operations fail | https://developers.cloudflare.com/durable-objects/platform/pricing/ |
| Workers AI | 10,000 neurons/day Free; Free allocation exhaustion fails instead of paid fallback on a Free plan | https://developers.cloudflare.com/workers-ai/platform/pricing/ |
| Static Assets | Assets can bind as `ASSETS` and Worker-first route `/api/*` | https://developers.cloudflare.com/workers/static-assets/binding/ |
| Workflows HITL | `step.waitForEvent` supports human approval waits; sleep/wait idle does not consume CPU | https://developers.cloudflare.com/workflows/build/events-and-parameters/ |
| Notion | average ~3 requests/second; 429 includes Retry-After; AriaOS defaults <=2 rps | https://developers.notion.com/reference/request-limits |
| Wrangler | v4 package; deployment/config CLI | https://www.npmjs.com/package/wrangler |

This repo keeps its own hard caps at or below 85% of these Free limits. Any deployment must rerun the preflight and refuse Paid migration if limits change adversely.

## ORDER-002 Amendment A1 revalidation

Reverified 2026-08-19 against current official Cloudflare documentation:

- Service Bindings call another Worker without a publicly accessible URL and are explicitly described as not increasing costs: https://developers.cloudflare.com/workers/runtime-apis/bindings/service-bindings/ and https://developers.cloudflare.com/workers/platform/pricing/ .
- Wrangler `services` is the supported binding configuration: https://developers.cloudflare.com/workers/wrangler/configuration/ .
- D1 `batch()` statements are SQL transactions; if a statement fails the sequence aborts/rolls back: https://developers.cloudflare.com/d1/worker-api/d1-database/ .

AriaOS therefore uses a private `aria-core → aria-effects` Service Binding and one D1 batch for state+outbox intent. A deployment preflight fails closed if this boundary cannot be represented on the current $0 surface.
