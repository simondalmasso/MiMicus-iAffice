# AriaOS

AriaOS is a zero-incremental-spend, evidence-backed Business Operating System for Cloudflare Workers. ORDER-003 is stacked on ORDER-002 plus binding Amendment A1 and adds a dynamic zero-cost compute market without expanding business-effect authority.

Business path: `EVENT → D1 → ROUTE → SPECIALIST → AUD → VERIFIED_KNOWLEDGE → CEO → ActionIntent → POLICY/APPROVAL → OUTBOX → aria-effects → RECEIPT → LEDGER`.

Compute path: `TASK → deterministic/no-model → ModelDataClass → cost/privacy/evidence/quality/health gates → durable quota reservation → deterministic route → aria-models → InferenceReceipt → quota commit`.

Capability domains are physical: `aria-core` routes and governs; `aria-effects` remains the only business-effect executor; `aria-models` is the only model-provider executor. The model gateway cannot perform business effects, and model output cannot grant effect authority.

Hard compute rules: monetary model spend authorization is zero. Billable inference, unknown price/billing, paid fallback, automatic upgrade/purchase/overage, and SECRET-to-model are denied. Stale or expired free evidence disables a route. Free exhaustion may use another independently eligible route or defer.

## Local reproducibility

```bash
npm ci --offline --ignore-scripts
npm run typecheck
npm test
npm run test:coverage
npm run e2e
npm run e2e:compute
npm run benchmark
npm run benchmark:compute
npm run chaos:compute
npm run security
npm run doctor
python scripts/ui_smoke.py
python scripts/ui_smoke_order003.py
```

The parent ORDER-002 reference E2E and >=10x benchmark remain regression gates.

## Operator CLI

```bash
npm run build
node scripts/aria.mjs compute status
node scripts/aria.mjs compute providers
node scripts/aria.mjs compute probe <provider>
node scripts/aria.mjs compute benchmark
node scripts/aria.mjs compute explain-route <task>
node scripts/aria.mjs compute verify-cost
node scripts/aria.mjs compute disable <provider-or-model>
node scripts/aria.mjs compute reconcile
```

Production compute read surfaces are `/api/compute/providers`, `/api/compute/models`, `/api/compute/routes`, `/api/compute/budget`, `/api/compute/incidents`, and `/api/compute/route/:taskId`. Mutation/probe operations use the existing admin-authenticated control plane.

The existing cockpit adds a Compute section while preserving Today, Tasks, Memory, Decisions, Approvals, Agents and System.

Third-party catalogs may discover candidates but never authorize them. OmniRoute discovery is pinned to `diegosouzapw/OmniRoute@3c9cb21cca443b8caef5aa180827a6989e258a95`; runtime does not depend on it.

See `docs/COMPUTE_MARKET.md`, `docs/PROVIDER_POLICY.md`, `docs/PROVIDER_ONBOARDING.md`, and `docs/COMPUTE_QUOTAS.md`.

Live ORDER-003 completion requires exact-head deployed evidence for Workers AI, a distinct direct first-party free provider, and controlled live fallback. Local or synthetic success cannot replace those live gates.
