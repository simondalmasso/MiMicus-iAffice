# Deployment

Target is two Cloudflare Workers plus shared Free-compatible resources.

`aria-effects` deploys first with `workers_dev=false`, shared D1, no AI/planner/scheduler binding and only effect-scoped secrets when an external write adapter is enabled. `aria-core` deploys second with static cockpit, D1, Workers AI, Queues+DLQ, SQLite Durable Object, Workflow and a private `EFFECTS` Service Binding to `aria-effects`. Core runtime secrets are `ADMIN_TOKEN_HASH`, `WEBHOOK_SECRET` and `APPROVAL_SIGNING_KEY`; the same approval signing key is required by effects only to validate terminal authorization. External write tokens must never be bound to core.

`scripts/cloudflare-preflight.mjs` checks credential names only, validates the two-worker boundary and denies paid model configuration. `scripts/render-wrangler.mjs` renders exact D1 ID/SHA into ignored generated configs. `scripts/deploy-cloudflare.sh` applies migrations, deploys `aria-effects`, then deploys `aria-core`, pinned to Wrangler 4.122.0.

Live acceptance requires core deployment URL/version, exact SHA at `/api/health`, effect-gateway SHA, migration state, live Workers AI inference, the full reference E2E through the Service Binding, persistence across redeploy/re-instantiation, and `$0` evidence.

If no authorized Cloudflare account/token is available in the execution/repository surfaces, local success cannot be represented as deployment. That external credential absence is a strict `BLOCKED_REAL` only after the rest of the branch/evidence package is complete.
