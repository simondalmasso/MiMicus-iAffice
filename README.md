# AriaOS

AriaOS is a zero-incremental-spend, evidence-backed Business Operating System for Cloudflare Workers. It normalizes business events, persists canonical state in D1, routes the minimum useful coalition of business roles, falsifies material claims with AUD, gates protected actions with one-time approvals, and records replayable/tamper-evident decisions.

Canonical flow:

`EVENT → NORMALIZE → D1 RAW TRUTH → ROUTE → SPECIALIST → AUD → VERIFIED KNOWLEDGE → CEO → ActionIntent → POLICY/APPROVAL → D1 OUTBOX → aria-effects → RECEIPT → LEDGER/REPLAY`

ORDER-002 is a clean-slate implementation. No Allora runtime is part of this tree.

## Roles

`CEO`, `RESEARCH`, `CMO`, `SALES`, `DATA`, `DEV`, and independent `AUD`. Roles are capability profiles invoked by `TaskRouter`; they are not permanent chats. Deterministic code and SQL run before model inference.

## Safety invariants

- `COST_HARD_CAP_USD=0`.
- Paid model/resource fallback is denied.
- Agents never execute external writes. `aria-core` emits digest-bound `ActionIntent`; only internal `aria-effects` can own write credentials or invoke write APIs.
- Customer sends, publication, merges and deploys require approval.
- Money mutation and credential mutation are disabled in V1.
- External text is untrusted data, never instruction authority.
- No LLM may directly create `VERIFIED_KNOWLEDGE`.
- One-time approvals bind to an exact payload hash and expire.
- Quota exhaustion defers optional work rather than spending.

## Clean checkout → local validation

Requirements: Node.js 22+ and Python 3.11+ only for the optional browser smoke. The application has no npm runtime dependencies.

```bash
npm ci --offline --ignore-scripts
npm run typecheck
npm test
npm run test:coverage
npm run security
npm run doctor
npm run e2e
npm run benchmark
python scripts/ui_smoke.py
```

Core coverage target is >=90% lines for policy, memory, router, ledger and budget modules.

## CLI

Build once, then run the checked-in CLI:

```bash
npm run build
node scripts/aria.mjs doctor
node scripts/aria.mjs ingest reference
node scripts/aria.mjs run reference-e2e
node scripts/aria.mjs tick
node scripts/aria.mjs replay
node scripts/aria.mjs verify-ledger
node scripts/aria.mjs compact-memory
node scripts/aria.mjs benchmark
node scripts/aria.mjs export-evidence
```

Local CLI state is under ignored `.aria/`. The browser/Cloudflare deployment uses D1 as canonical memory.

## Reference-business E2E

The credential-free `REFERENCE_BUSINESS_FIXTURE` contains 20 leads, 20 content observations, seven days of funnel metrics, sourced research, contradictory facts, a prompt-injection payload, a hot lead, a stale lead, a funnel anomaly and a simulated incident.

`npm run e2e` executes the mandatory chain through ingestion, deduplication, deterministic metrics, Sales/Data/Research/CMO/CEO/Dev/AUD, approval gating, transactional ActionIntent outbox, private Effect Gateway, idempotent SafeOutbound reference effect, restart/replay, tamper detection, model accounting and zero-cost proof. Fixture data is never represented as real customer data.

## Browser cockpit

`apps/cockpit/index.html` provides Today, Tasks, Memory, Decisions, Approvals, Agents and System views. It reads the Worker API and never renders secret values. Mutations use a bearer admin token held only in page memory; no token is stored in localStorage.

## Cloudflare deployment

The production architecture uses two Workers: `aria-core` (cockpit, D1, Workers AI, Queues, Durable Object, Workflows) and internal-only `aria-effects`, connected by a Service Binding. `wrangler.core.template.jsonc` contains no external write credentials; `wrangler.effects.template.jsonc` contains no AI/planner binding and has `workers_dev=false`.

1. Authenticate Wrangler with a least-privilege Cloudflare API token. Do not paste the token into repo files.
2. Create D1 `ariaos-v1` and queues `ariaos-events-v1` / DLQ if they do not exist.
3. Set `CLOUDFLARE_D1_DATABASE_ID` and exact `ARIA_HEAD_SHA` in the deployment shell.
4. Set core secrets with Wrangler: `ADMIN_TOKEN_HASH`, `WEBHOOK_SECRET`, and `APPROVAL_SIGNING_KEY`; set the same `APPROVAL_SIGNING_KEY` on effects for signature verification. Any optional GitHub/Notion write token belongs only to `aria-effects`.
5. Render and deploy:

```bash
node scripts/cloudflare-preflight.mjs
node scripts/render-wrangler.mjs
./scripts/deploy-cloudflare.sh
```

The deploy script pins Wrangler 4.122.0, applies D1 migrations remotely, then deploys the Worker. The generated config is ignored by Git.

After deployment:

```bash
curl -fsS https://<worker>/api/health
curl -fsS https://<worker>/api/system/budget
curl -fsS -X POST -H "Authorization: Bearer $ARIA_ADMIN_TOKEN" https://<worker>/api/reference-e2e
```

A valid DONE checkpoint requires the live reference E2E to execute Workers AI on the deployed Free-compatible configuration and evidence to record URL, deployment/version identifier, SHA and migration state. Absence of authorized Cloudflare credentials is handled only as the strict external `BLOCKED_REAL` defined by ORDER-002 after local completion.

## Evidence

Deterministic and live evidence belongs in `evidence/ORDER-002/`. Every material claim is typed as `LIVE_DEPLOYED`, `LIVE_EXTERNAL`, `OFFICIAL_DOC`, `SOURCE_CODE`, `DETERMINISTIC_TEST`, `DERIVED`, `REFERENCE_FIXTURE`, `ASSUMPTION`, or `UNKNOWN`.

See `docs/AUDIT_EVIDENCE.md` for gate mapping and `docs/DEPLOYMENT.md` for the live procedure.
