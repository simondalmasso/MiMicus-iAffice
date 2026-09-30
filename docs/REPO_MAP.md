# Repository map — ORDER-004

Canonical entry points:

| Area | Path | Authority |
|---|---|---|
| Public control plane | `apps/worker/src/index.ts` | routes/API/Queue/Workflow only |
| Operator UI | `apps/cockpit/index.html` | UI only |
| Model boundary | `apps/model-worker/` | model/provider execution only |
| Business effects | `apps/effects-worker/` | protected external writes only |
| Heavy cloud jobs | `apps/oracle-executor/` | typed non-canonical jobs only |
| Revenue/CASE logic | `packages/sniper/src/` | domain logic |
| Policy | `packages/policy/src/` | authority gates |
| Memory | `packages/memory/src/` | canonical memory model |
| Compute routing | `packages/router/src/` | zero-cost route selection |
| D1 schema | `migrations/0001..0011` | canonical durable schema |
| Current checkpoint | `docs/CHECKPOINT_ORDER_004.md` | continuation source |
| Cloudflare deploy | `docs/DEPLOYMENT.md` | canonical deploy runbook |
| Oracle runtime | `docs/ORACLE_EXECUTOR_RUNBOOK.md` | cloud executor/runner runbook |

Canonical Wrangler templates:
- `wrangler.core.template.jsonc`
- `wrangler.models.template.jsonc`
- `wrangler.effects.template.jsonc`

Generated deployment files go under `.generated/` and are never committed.

Historical ORDER-002/003 scripts/docs may remain for regression evidence. They are not the current operator path unless README, ORDER-004 checkpoint or package scripts explicitly call them.

Do not create:
- another control plane;
- another canonical database;
- another generic Wrangler template;
- a Simon-PC runner;
- arbitrary-shell executor endpoints.
