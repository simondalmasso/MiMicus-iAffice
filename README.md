# iAffice

iAffice is a cloud-first autonomous revenue operating system for evidence-backed local business discovery, CASE evaluation, private demos, negotiation support, delivery, payment orchestration and audited learning.

Current work is ORDER-004 on branch `order-004-sniper-autonomous-revenue-engine-v1`, stacked on ORDER-003.

## Runtime

Public control plane:
- `agent-os` — Cloudflare Worker + cockpit
- target: `https://agent-os.simondalmasso44.workers.dev/`

Private capability boundaries:
- `aria-models` — model/provider execution only
- `aria-effects` — external business writes only
- Oracle Free Tier executor — typed heavy/demo jobs only; non-canonical

Canonical state:
- Cloudflare D1
- Queues / DLQ
- Durable Objects
- Workflow

The operator browser is UI only. Simon's PC is not a runtime dependency.

## Core flow

```text
public business evidence
→ Discovery
→ one business = one CASE
→ local evaluation
→ Global Decision Core
→ specialist work
→ private Demo Job
→ AUD
→ evidence-backed outreach / negotiation
→ HUMAN_GATE when required
→ aria-effects
→ delivery / payment receipt
→ audited episodic + semantic learning
→ future prioritization
```

## Hard invariants

- incremental monetary model/runtime spend target = USD 0;
- unknown/billable routes fail closed;
- no agent/model can directly perform protected external writes;
- no fake uplift, fake facts, fake stock, fake price or invented measurements;
- only public business contact data is eligible for discovery/outreach;
- private demos are not production;
- action-bound approval remains mandatory where policy requires it;
- Oracle never owns canonical business state;
- no arbitrary-shell executor API;
- exact-head evidence is required before merge/deploy claims.

## Current operator surfaces

Cockpit:
`Revenue / Global Core / Operations / Discovery / Demos / Cases / Live / Decisions / Learning / Telemetry / Skills / Squad / Approvals / Compute / System`

Key APIs:
- `/api/health`
- `/api/sniper/global`
- `/api/sniper/operations`
- `/api/sniper/discovery/*`
- `/api/sniper/demos`
- `/api/sniper/executors`
- `/api/sniper/telemetry`
- `/api/compute/*`

## Verification

Canonical ORDER-004 gate:

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
python3 scripts/oracle_executor_selftest.py
npm run doctor:004
python3 scripts/ui_smoke_order004.py
```

GitHub Actions is restricted to:
`[self-hosted, linux, oracle-free, iaffice]`

Do not silently run ORDER-004 on Simon's Windows PC or a potentially billable hosted runner.

## Cloudflare deploy

Canonical templates:
- `wrangler.core.template.jsonc`
- `wrangler.models.template.jsonc`
- `wrangler.effects.template.jsonc`

Canonical deploy:

```bash
npm run deploy:preflight
npm run deploy:config
npm run deploy:cloudflare
```

Generated Wrangler files live only under `.generated/`.

See:
- `docs/CHECKPOINT_ORDER_004.md` — exact present-tense continuation state
- `docs/DEPLOYMENT.md` — Cloudflare deploy
- `docs/ORACLE_EXECUTOR_RUNBOOK.md` — Oracle executor/runner
- `docs/ARCHITECTURE.md`
- `docs/MEMORY_MODEL.md`

## Commercial safety

CASE-linked external commercial actions use a dedicated durable gate before ActionIntent creation and are revalidated again inside `aria-effects`.

Current rules include:
- public-business contact provenance only;
- durable opt-out / explicit refusal;
- max 3 autonomous persuasive contacts per rolling 30-day window;
- minimum 48-hour cooldown;
- exact-payload `COMMERCIAL_COPY_GUARD` AUD PASS for outreach/proposals/meeting messages;
- no bulk blast, false urgency, unsupported claims or human impersonation;
- current HUMAN_GATE revalidation;
- accepted offer required before payment-request paths;
- customer approval required before customer deployment/credential handoff;
- verified payment required before invoice/receipt paths.

Only currently implemented safe outbound adapters are exposed. Missing payment/deploy/publish adapters fail closed rather than creating dead approvals.
