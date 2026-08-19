# Deployment

ORDER-003 deploys three capability domains: private `aria-models`, private `aria-effects`, then control-plane `aria-core`, plus existing D1/Queues/Workflows/Durable Objects.

`wrangler.models.template.jsonc` has `workers_dev=false` and model execution bindings only. `wrangler.effects.template.jsonc` remains private and contains effect-domain bindings only. `wrangler.core.template.jsonc` contains D1, private Service Bindings `MODELS` and `EFFECTS`, queues/workflows and two Durable Objects; it does not directly invoke model vendors or business-effect vendors.

Deployment sequence:

```bash
node scripts/cloudflare-preflight.mjs
node scripts/render-wrangler.mjs
./scripts/deploy-cloudflare.sh
```

The deploy script applies both D1 migrations, then deploys models, effects and core using pinned Wrangler. Exact code SHA and D1 identifier are supplied by the authorized deployment environment and are never committed.

Live acceptance requires exact SHA/version from all three Workers; remote migration state; a real Workers AI benchmark/call; a distinct direct first-party Free provider benchmark/call; controlled safe fallback; sanitized inference receipts; durable quota reconciliation; parent reference E2E; no effect-authority expansion; and cumulative monetary spend USD 0.

If the execution environment lacks authorized deployment/account access or a distinct external provider capability, local success is recorded but cannot be promoted to the live gates.
