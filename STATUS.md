# MiMicus iAffice — Verified operational status (2026-10-09)

**Canonical product branch:** `main`  
**Last code release checkpoint:** `9f743b9cba4039e7a77ebb57700a6da49e413a81` (PR #35 merged)  
**Exact code-checkpoint CI:** [Mimicus CI #37912600704](https://github.com/simondalmasso/MiMicus-iAffice/actions/runs/37912600704) — **SUCCESS**  
**Production release:** [one-shot release #37914241111](https://github.com/simondalmasso/MiMicus-iAffice/actions/runs/37914241111) — **SUCCESS**  
**Cloudflare Worker version observed in deploy log:** `52b15ef2-6c3c-485e-8f3d-b7e175346579`  
**Public origin:** https://mimicus.simondalmasso44.workers.dev/

## What is LIVE_OBSERVED

The Cloudflare cockpit serves real HTTP status for its own Worker, not for the separate Python orchestration runtime.

On 2026-10-09, the release workflow and independent endpoint probes verified:

- `/`, `/app.js`, `/styles.css`: HTTP 200 and five required security headers.
- `/health`, `/api/health`, `/api/runtime`, `/api/status`: HTTP 200, JSON responses and security headers.
- Unknown `/api/*` routes, including `/api/activity` when no observer is hosted: HTTP 404, JSON, security headers.
- `/api/status` exposes `coreConnected:false`, `agentActivityAvailable:false`, and `externalEffectsEnabled:false`.
- Public cockpit has no fabricated metrics, simulated agent presence, autoplay event logs or synthetic autopilot control.
- Asset-first security headers use Cloudflare `public/_headers` (PR #34) to cover direct static asset delivery without per-request Worker CPU.

`LIVE_OBSERVED` on this public endpoint describes **the Cloudflare edge response only**. It does NOT prove that the Python LAYA core, model inference, autonomous agents, business lead ingestion, messages or remote chat are running.

## What is VERIFIED_AT_HEAD (repository core)

PR #35 exact-head and post-merge CI passed the package and cockpit release gates. The post-merge core job logged:

- **290 tests passed** (5 warnings);
- >=90% total coverage gate passed;
- Ruff, mypy (109 source files), build, deterministic commercial triage and funnel smoke PASS;
- cockpit syntax, DOM/provenance truth contract and pinned Wrangler dry-run PASS.

`core/` contains LAYA / `MiMicusEngine`, completion-driven DAG scheduler, governed memory, commercial decision gates, causal replay, effect authorization and read-only observer code. These are **implemented and CI-verified**, but code in the repository is not automatically a running public service.

## What remains NOT OPERATIONAL in the public site

1. **LAYA runtime connection:** The Python process is not deployed inside the Worker and has no public authenticated bridge to the cockpit.
2. **Real group chat:** No real agent-to-agent chat room, live per-agent sessions or authenticated event stream is attached to production.
3. **Real business telemetry:** No configured real setter ledger is connected to the Worker. No sales, income or leads should be inferred.
4. **Real model inference:** Default offline/scripted provider is suitable for deterministic testing/orchestration, **not** an independently reasoning hosted model. NVIDIA NIM requires its own credential and confirmed entitlement.
5. **Autonomous external actions:** Denied by default; exact-envelope human approval and authorized adapters remain required.

The existing local observer is intentionally read-only and loopback-only, at `http://127.0.0.1:8788/` once explicitly started with a real ledger. It must never be mistaken for a hosted chat service. The public `/api/activity` returns JSON 404 because no remote observer is connected.

## Cost and security

- Baseline package/observability architecture has no mandatory paid model service; Cloudflare/GitHub usage remains subject to free-plan eligibility and limits. This is **not** an assertion that the account has never incurred charges.
- Cloudflare Worker has only static assets/Worker bindings; no persistent chat storage, D1, Durable Objects, KV or Workers AI are provisioned.
- No public LAYA command ingress, unreviewed mutations, effect adapters or secret values in the client.
- Other project or historical branches do not supersede canonical `main`; divergent branches are preserved, not deleted.

## Next actual product milestone

Ship an **authenticated, evidence-backed LAYA event bridge** from a running Python control plane, including explicit source provenance, bounded/persisted redacted event storage and reader access control. Only then build agent group-room UI from actual emitted events. No fake agents, metrics, messages, schedules or credentials may be generated as a stand-in.

This document is a checkpoint of the exact named code release and live deployment; a subsequent documentation-only commit does not imply production runtime drift.
