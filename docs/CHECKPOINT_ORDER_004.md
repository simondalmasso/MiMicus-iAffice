# ORDER-004 CHECKPOINT — Autonomous Revenue Engine

Updated: 2026-09-28
Status: ACTIVE / IMPLEMENTED PARTIAL / NOT VERIFIED / NOT MERGE-READY

Reference implementation HEAD immediately before this checkpoint refresh: `be4aab51872d112365788aab8fd69fef7322ea8a`. Always fetch the live branch HEAD before continuing; do not assume this reference SHA is current.
Parent drift at this checkpoint: base/merge-base remains `204ae12a74dd451561dc801631d671d35e65dd56`; ORDER-004 is 54 commits ahead and 0 behind.

## READ THIS FIRST

You are continuing a cloud-only implementation. Do not use the user's PC.

Do not manually analyze named businesses supplied in chat and encode your conclusion as product logic.
Named businesses/websites are examples, fixtures, or validation cases only.

The system itself must:
observe → collect evidence → diagnose → rank opportunity → choose what to offer → choose what NOT to offer → build proof/demo → decide next move → negotiate → deliver → collect → audit outcome → learn.

## Canonical Git state

Repository:
`simondalmasso/AriaOS`

ORDER:
GitHub issue #7
`ORDER-004 — Autonomous Revenue Engine v1 — cloud swarm, cognition, memory, live operations`

Implementation branch:
`order-004-sniper-autonomous-revenue-engine-v1`

Stacked parent:
`order-003-zero-cost-compute-market-v1`

Exact parent SHA when ORDER-004 branch was created:
`204ae12a74dd451561dc801631d671d35e65dd56`

Do NOT rebase silently. Before any future merge, compare parent drift and record it.

ORDER-002 Amendment A1 remains binding:
agents/models do not directly write externally.
All business external effects remain behind `aria-effects`.

ORDER-003 remains binding:
zero monetary model spend; no paid fallback; inference stays behind `aria-models`.

## Current product definition

This is the web/cloud environment where an autonomous specialist company lives.

It is NOT:
- a collection of chatbots;
- a manual prospect analysis tool;
- a prompt demo;
- a user-PC automation.

It IS:
- cloud control plane;
- durable company state;
- specialist agent squad;
- cognitive/orchestration layer;
- durable memory and audited learning;
- external effect boundary;
- operator dashboard.

The operator dashboard is the primary human surface. It shows work and business state, not internal model theatre.

## Current specialist squad

Implemented in `packages/sniper/src/engine.ts`:

- ORCHESTRATOR
- SCOUT
- MARKET_RESEARCH
- QUALIFIER
- SALES
- NEGOTIATOR
- UX_AUDITOR
- WEB
- DESIGN
- SOCIAL
- CATALOG
- CRM
- AUTOMATION
- PAYMENTS
- PRODUCT
- ANALYTICS
- COPY
- DEMO
- DELIVERY
- AUD
- MEMORY

Rule:
Recurring outcome ownership = agent.
Reusable know-how = skill/tool.

## Current cognitive architecture

Implemented in `packages/sniper/src/cognition.ts`.

Decision engine currently:
- receives opportunity context;
- ranks candidate next moves;
- uses context fit;
- incorporates learned tactic score;
- applies contact-fatigue penalty;
- applies follow-up timing;
- respects HUMAN_GATE;
- persists selected move, tactic, score, reasons, alternatives.

Current moves:
- ENRICH_CONTACT
- BUILD_DEMO
- SEND_DIAGNOSTIC
- FOLLOW_UP_WITH_VALUE
- NEGOTIATE
- SEND_PROPOSAL
- DELIVER
- COLLECT
- ESCALATE_HUMAN
- DEFER

This is a deterministic cognition skeleton. It is intentionally inspectable.
Later model reasoning may propose candidates/arguments, but deterministic policy/evidence/memory must remain the authority envelope.

## Memory / relearning architecture

This is mandatory. The system is useless without it.

1. WORKING MEMORY
   Current opportunity dossier and current state.

2. EPISODIC MEMORY
   What happened:
   interaction, objection, tactic, decision, outcome, artifact, evidence.

3. SEMANTIC MEMORY
   Reusable patterns supported by multiple audited outcomes.
   Schema exists; promotion logic needs expansion.

4. PROCEDURAL MEMORY
   Which tactics/skills perform better under which contexts.

Implemented:
- `sniper_memory_episodes`
- `sniper_decision_trace`
- `sniper_semantic_patterns`
- `sniper_tactic_learning`

Hard rule:
No unaudited response/model opinion may change durable strategy.
Only attributed + evidenced + audited outcomes can promote learning.

## Opportunity engine

Implemented in `packages/sniper/src/engine.ts`.

Current evidence-grounded signals include:
- visible demand/rating/review volume;
- no website;
- weak website quality;
- no ecommerce;
- no CRM;
- no WhatsApp automation;
- no online payments;
- no analytics;
- weak social presence;
- public contact path.

Current output:
- score;
- reasons;
- recommended primary services;
- secondary services;
- evidence refs;
- persuasion case.

Quantitative sales rule:
Never invent "you will sell X% more".
Observed facts and hypothetical scenarios are separate.
Forecasts require explicit input assumptions.

## Vertical service packs

Implemented in `packages/sniper/src/servicePacks.ts`.

Current:
- OPENINGS_COMMERCE
- REAL_ESTATE_IMMERSIVE
- LOCAL_COMMERCE_DIGITAL
- SERVICE_BUSINESS_CRM

These are reusable patterns.

Important:
Do NOT hardcode any named example company.

Current 3D/reconstruction references:
- VIGA: MIT; generate-render-verify pattern; GPU/API-heavy runtime.
- Unreal Home Wizard: Apache-2.0; useful evidence/photo-match workflow; Unreal 5.8 heavy runtime.

Cloudflare Worker is the control plane.
Heavy 3D/browser/build workloads must be isolated cloud jobs, not synchronous Worker request execution.

## Durable D1 state

Migrations:

`migrations/0003_sniper_revenue_engine.sql`
- sniper_opportunities
- sniper_negotiations
- sniper_deliveries
- sniper_payments
- sniper_tactic_learning
- sniper_activity

`migrations/0004_sniper_cognitive_memory.sql`
- sniper_memory_episodes
- sniper_decision_trace
- sniper_semantic_patterns

Store:
`packages/sniper/src/store.ts`

Current store functions include:
- ingest opportunity;
- list/get opportunity;
- set status;
- record negotiation;
- record payment;
- record activity;
- learn tactic;
- record episode;
- select/persist cognitive next move;
- memory summary;
- dashboard projection.

## Worker API

Implemented in `apps/worker/src/index.ts`.

Current read endpoints:
- GET `/api/sniper/dashboard`
- GET `/api/sniper/opportunities`
- GET `/api/sniper/opportunities/:id`
- GET `/api/sniper/activity`
- GET `/api/sniper/squad`
- GET `/api/sniper/memory`

Current protected write endpoints:
- POST `/api/sniper/opportunities/ingest`
- POST `/api/sniper/decision`
- POST `/api/sniper/episode`
- POST `/api/sniper/feedback`
- POST `/api/sniper/negotiation`
- POST `/api/sniper/payment`

Existing core auth/rate-limit behavior applies to non-GET API operations.

## Dashboard

Implemented/rebuilt in:
`apps/cockpit/index.html`

Current sections:
- Revenue
- Cases
- Live
- Decisions
- Learning
- Squad
- Approvals
- Compute
- System

Current UI refreshes cloud state approximately every 8 seconds.

Dashboard design goal:
minimal / modern / editorial / quiet / operational.
No hacker aesthetic, no neon, no agent-swarm theatre.

## Tests

Contract tests:
`tests/sniper.test.mjs`

Coverage currently targets:
- opportunity scoring;
- offer selection;
- evidence-grounded persuasion;
- HUMAN_GATE;
- squad roles;
- audited tactic learning;
- dashboard projection;
- openings service pack;
- real-estate immersive service pack;
- no hardcoded case-study target;
- cognitive HUMAN_GATE;
- demo-before-outreach behavior;
- learned tactic ranking;
- audited memory promotion.

IMPORTANT:
These tests have NOT been executed in a verified cloud runner yet.

Do not claim PASS.

## Verification blocker

No registered Codex Tasks cloud environment is currently available.

Existing workflow:
`.github/workflows/verify.yml`

Current workflow facts:
- uses `runs-on: self-hosted`;
- push trigger is ORDER-003 branch;
- PR trigger targets ORDER-002 branch.

The user explicitly requires:
NO user PC.

Therefore:
G16 cloud build/typecheck/test verification is currently BLOCKED by runner availability/configuration.

Do not silently switch to a potentially billable hosted runner.
Zero-cost invariant still applies.

## External effects / outreach

Do not bypass A1.

Future email, WhatsApp, payment, deploy, publishing, CRM writes must flow:

`decision → ActionIntent → policy/AUD/HUMAN_GATE → durable state/outbox → aria-effects → connector → receipt → ledger`

Do not hide an AI as a named human.
Company/brand-based communication may be natural and persuasive, but factual identity/claims must not be fabricated.

## HUMAN_GATE

Current deterministic triggers include:
- buyer requests human meeting/video call;
- large configured amount;
- non-standard commercial terms;
- legal commitment.

Extend later for:
- high reputational risk;
- ambiguous authorization;
- contract/signature requirements;
- exceptional concessions;
- regulated/sensitive work.

Simon handles face-to-face/video when required.

## WHAT TO DO NEXT — EXACT ORDER

A fresh GPT/ARQ should:

1. Read GitHub issue #7 completely.
2. Read this checkpoint completely.
3. Fetch current branch HEAD of `order-004-sniper-autonomous-revenue-engine-v1`.
4. Compare it to `order-003-zero-cost-compute-market-v1`; record parent drift.
5. Inspect:
   - packages/sniper/src/engine.ts
   - packages/sniper/src/cognition.ts
   - packages/sniper/src/servicePacks.ts
   - packages/sniper/src/store.ts
   - apps/worker/src/index.ts
   - apps/cockpit/index.html
   - migrations/0003_sniper_revenue_engine.sql
   - migrations/0004_sniper_cognitive_memory.sql
   - tests/sniper.test.mjs
6. Do a syntax/type review before adding scope.
7. Obtain a cloud-only zero-cost verification path. Do NOT use Simon's PC.
8. Run at minimum:
   - npm run typecheck
   - npm test
   - npm run security
   - npm run architecture
   - relevant UI smoke
9. Fix all failures before claiming anything.
10. Expand SEMANTIC MEMORY promotion:
    - multi-episode support;
    - contradiction counts;
    - category/locality/context scoping;
    - confidence decay;
    - supersession.
11. Add SKILL REGISTRY:
    - source;
    - license;
    - version/commit;
    - role compatibility;
    - runtime;
    - cost class;
    - network permissions;
    - data class allowed;
    - benchmark;
    - health;
    - promotion/disable state.
12. Add DISCOVERY JOB contract:
    - locality/category query;
    - public data provenance;
    - dedupe;
    - crawl/browser adapter;
    - website audit;
    - contact enrichment;
    - opportunity ingestion.
13. Add DEMO JOB contract:
    - service pack;
    - evidence input;
    - isolated build sandbox;
    - preview URL;
    - artifact manifest;
    - AUD gate.
14. Add DELIVERY and COLLECTION state transitions.
15. Add effects connectors only through aria-effects.
16. Add operator visibility for all of the above.
17. Re-run all gates.
18. Update THIS checkpoint in present tense before ending every substantial work session.
19. Preserve the invariant **one business = one case**. New commercial/evidence/learning features should attach to the case dossier instead of creating disconnected parallel records.

## Near-term architecture direction

Cloudflare:
- dashboard/assets;
- API/control plane;
- D1;
- Queues;
- Workflows;
- Durable Objects;
- aria-models;
- aria-effects.

Oracle Free Tier candidate:
- isolated heavier workers;
- browser automation;
- build/render jobs;
- possible CPU-heavy inference;
- possible 3D preprocessing.

Oracle must be treated as optional executor behind an interface.
Do not couple core state or orchestration to one VM.

## Non-goals for the immediate next turn

Do NOT:
- buy anything;
- provision paid compute;
- purchase WhatsApp/SIM resources;
- send real outreach;
- charge customers;
- deploy customer sites;
- merge ORDER-004;
- rename the repo;
- hardcode example businesses.

## Definition of progress

Progress means the COMPANY SYSTEM gains a capability.

Manual analysis of one example prospect is not progress unless it produces:
- a generalized signal;
- a generalized service pack;
- a test;
- a decision rule;
- a reusable skill;
- a benchmark;
- or a reusable evidence/audit mechanism.

## Cases / per-business dossiers

Current rule:
**one business = one case**.

Implemented:
- `packages/sniper/src/case.ts` — canonical case dossier projection.
- `GET /api/sniper/cases/:id` — case dossier endpoint.
- `apps/cockpit/index.html` — Cases operator workspace.

A case currently exposes:
- business identity/category/locality;
- current status/owner/next action;
- opportunity score/reasons;
- evidence references;
- observed facts;
- inferred recommendation;
- demo brief;
- contacts;
- negotiation history;
- objections/concessions;
- HUMAN_GATE state;
- cognitive decisions and alternatives;
- case-specific memory episodes;
- deliveries;
- payments;
- complete activity timeline.

The dashboard now supports:
- **BOARD** view grouped by commercial stage;
- **CARDS** view for scan/browse;
- **CASE DETAIL** for the full dossier.

Current board groups:
- DISCOVERY
- QUALIFIED
- CONTACT
- DEAL
- DELIVERY

Important:
The UI groups cases for operator visibility only.
Case state remains canonical in D1; the board does not create a separate source of truth.

## Global Decision Core

There are now TWO cognition levels.

### 1. GLOBAL CORE — company level

Implemented in:
- `packages/sniper/src/globalCore.ts`
- `migrations/0005_sniper_global_core.sql`
- `packages/sniper/src/store.ts`
- `apps/worker/src/index.ts`
- `apps/cockpit/index.html`

Purpose:
see the whole portfolio at once and decide where the company spends scarce attention.

The Global Core currently:
- ranks all cases globally;
- applies strategic-tag fit;
- considers evidence sufficiency;
- considers contactability;
- considers demo readiness;
- considers idle/stale cases;
- isolates HUMAN_GATE cases;
- allocates a bounded number of active cases;
- assigns owner role + next objective;
- persists every portfolio plan and allocation;
- exposes latest global plan to the dashboard;
- recalculates automatically on Cloudflare `business_tick`.

Current default business-tick policy:
- maxConcurrentCases = 8
- minEvidenceCount = 2
- preferredTags = []

Do not hardcode Santa Fe or a vertical into the core policy. Market focus belongs in configurable goals/policy.

### 2. CASE CORE — one business level

Implemented primarily in:
- `packages/sniper/src/cognition.ts`
- `packages/sniper/src/case.ts`

Purpose:
decide the next move INSIDE one business case.

The Case Core handles:
- enrich contact;
- build demo;
- send diagnostic;
- follow up with value;
- negotiate;
- send proposal;
- deliver;
- collect;
- escalate human;
- defer.

### Laya / System-1 architecture

Laya is NOT treated as another sales agent.

It is a candidate **System-1 typed decision coprocessor** for the Global Core and selected case decisions.

Verified from upstream repository:
- Laya is a multilingual non-autoregressive decision engine.
- It accepts typed questions:
  - choice
  - score
  - noul
- It returns probabilities/confidence and supports abstention thresholds.
- It does not generate sales copy.
- Node/ONNX runtime exists but published weights are large enough that this should NOT live inside a normal Cloudflare Worker process.

Architecture direction:

`Cloudflare Global Core state → typed decision request → optional Laya service on isolated cloud executor/Oracle → calibrated result/confidence → deterministic policy envelope → System-2 if needed → persisted global decision`

Current state:
- `buildGlobalTypedQuestions()` exists.
- `interpretGlobalSystemOne()` exists.
- confidence/abstention semantics exist.
- dashboard exposes Laya-compatible System-1 status.
- actual live Laya service is NOT CONNECTED yet.

Do not claim Laya runtime is deployed.

If/when connecting Laya:
- run it behind an interface;
- pin model/runtime revision;
- record license/model evidence;
- expose health/latency;
- use confidence threshold;
- preserve deterministic fallback;
- never let it create external effects.

### Global D1 tables

`migrations/0005_sniper_global_core.sql` adds:
- sniper_global_goals
- sniper_global_decisions
- sniper_global_allocations

Every global decision stores:
- portfolio hash;
- policy;
- global ranking;
- active cases;
- deferred cases;
- human-attention cases;
- System-1 result when available;
- reasons;
- timestamp.

### Global API

Read:
- GET `/api/sniper/global`

Protected write:
- POST `/api/sniper/global/plan`

The scheduled Cloudflare `business_tick` also computes/persists a global plan automatically.

### Global dashboard

Dashboard section:
`Global Core`

It shows:
- total portfolio;
- active allocations;
- human-attention count;
- System-1/Laya-compatible state;
- System-1/System-2/authority architecture;
- active allocations by owner/objective;
- global case ranking;
- HUMAN_GATE queue;
- deferred portfolio.

This is distinct from `Cases`.

`Global Core` answers:
**What should the company do now?**

`Cases` answers:
**What is happening with this specific business?**

## Updated continuation order after Global Core

Before adding more specialist agents or connectors, a fresh GPT should also inspect:
- packages/sniper/src/globalCore.ts
- packages/sniper/src/case.ts
- migrations/0005_sniper_global_core.sql

Then:
1. cloud-verify typecheck/tests/security;
2. connect audited procedural memory to global ranking instead of current neutral `auditedWinRate=0`;
3. implement contextual semantic-memory promotion;
4. implement versioned skill registry;
5. implement discovery jobs;
6. implement demo jobs;
7. only then connect optional Laya service behind a cloud interface;
8. preserve Cloudflare as source of truth/control plane;
9. keep Oracle optional and stateless relative to canonical D1 state.

## Five-stage operating model

The company now has one canonical operating model:

`ANALYZE → PROSPECT → EXECUTE → DELIVER → COLLECT`

Implemented:
- `packages/sniper/src/operatingModel.ts`
- `SniperStore.operationsOverview()`
- GET `/api/sniper/operations`
- dashboard section `Operations`

Canonical labels:
- ANALYZE = Analizan
- PROSPECT = Prospectan
- EXECUTE = Ejecutan
- DELIVER = Entregan
- COLLECT = Cobran

Every business remains one CASE.
Each CASE is projected into exactly one current operating stage from durable status.

External effects remain explicit.
Examples:
- SEND_OUTREACH → SEND_EXTERNAL
- DEPLOY_CUSTOMER_WORK → DEPLOY
- CREATE_PAYMENT_REQUEST → MONEY_MUTATION
- ISSUE_INVOICE → MONEY_MUTATION

The five-stage board does not bypass A1.

## Commercial autonomy policy

Implemented:
`packages/sniper/src/commercialPolicy.ts`

Purpose:
allow high-speed, evidence-backed autonomous selling without teaching the system spam, fabrication, coercion or unauthorized money/deploy behavior.

Current hard denials include:
- explicit refusal / opt-out → DO_NOT_CONTACT;
- unverified contact provenance;
- bulk blast;
- unsupported claims;
- false urgency;
- human impersonation;
- autonomous contact-fatigue limit;
- contact cooldown;
- payment request before accepted offer;
- production deploy without customer approval;
- invoice without verified payment;
- credential handoff without approval.

Current default autonomous-contact limits:
- max autonomous contacts in window: 3
- minimum interval: 48 hours

These defaults are policy constants and may later be made jurisdiction/channel-aware.
Do not relax them silently.

## Canonical observability fabric

Implemented:
- `packages/sniper/src/telemetry.ts`
- `migrations/0006_sniper_observability.sql`
- `SniperStore.recordTelemetrySpan()`
- `SniperStore.telemetryTrace()`
- `SniperStore.telemetryOverview()`
- GET `/api/sniper/telemetry`
- GET `/api/sniper/telemetry/traces/:traceId`
- protected POST `/api/sniper/telemetry/span`
- dashboard section `Telemetry`

Telemetry authority:
`ARIA_TELEMETRY_FABRIC`

Design:
- OpenTelemetry-compatible contract direction;
- OpenInference-compatible semantic direction;
- metadata/digests only by default;
- raw prompts/responses are NOT stored by the canonical schema;
- trace_id / span_id / parent_span_id;
- CASE linkage;
- agent role;
- operating stage;
- agent/model/tool/decision/memory/effect/job/policy kinds;
- status;
- latency;
- model/provider;
- input/output tokens;
- actual monetary cost;
- error code;
- input/output digests;
- typed attributes.

Hard invariant:
`actualCostUsd > 0` is rejected by canonical telemetry because ORDER-003 zero-spend remains binding.

Automatic instrumentation currently exists for:
- GLOBAL_CORE portfolio plan decisions;
- ORCHESTRATOR next-move decisions.

All future specialist/tool/model/effect runtimes should emit spans through this contract.

Dashboard Telemetry currently exposes:
- trace count;
- span count;
- errors / denied / abstained;
- p95 latency;
- input/output tokens;
- actual spend;
- health grouped by agent;
- recent spans;
- trace explorer with parent→child tree;
- adapter/reference registry.

### Verified observability-source status

Verified from current upstream repositories before this checkpoint:

- Langfuse:
  - repo exists;
  - self-hosted tracing;
  - core is MIT-style but EE directories are separately licensed;
  - REFERENCE_ONLY until exact reused surface is pinned.

- AgentOps:
  - MIT;
  - agent monitoring/session replay/self-hosting;
  - REFERENCE_ONLY.

- Laminar (`lmnr-ai/lmnr`):
  - Apache-2.0;
  - OpenTelemetry-native;
  - realtime traces + SQL/dashboard;
  - ADAPTER_CANDIDATE.

- Dify:
  - modified Apache-2.0 with additional conditions including multi-tenant restrictions;
  - REFERENCE_ONLY, not platform dependency.

- Flowise:
  - upstream repository is archived;
  - REJECT as new dependency.

- Arize Phoenix:
  - OpenTelemetry/OpenInference;
  - current repo license is Elastic License 2.0;
  - REFERENCE_ONLY due hosted/managed-service restrictions.

- OpenLIT:
  - Apache-2.0;
  - OpenTelemetry-native agent/tool/model/token/cost telemetry;
  - ADAPTER_CANDIDATE.

- Helicone:
  - Apache-2.0;
  - tracing/cost/gateway capabilities;
  - REFERENCE_ONLY because gateway role overlaps with `aria-models`.

- AutoGen Studio:
  - AutoGen upstream explicitly states maintenance mode;
  - REJECT as new dependency.

- Observra:
  - Apache-2.0;
  - framework-agnostic agent telemetry and OTel export;
  - ADAPTER_CANDIDATE.

Do NOT install multiple observability platforms into the control plane.
If an external backend is later used, export canonical spans to ONE selected backend at a time through an adapter.

## Orchestration reference registry

Implemented:
`packages/sniper/src/orchestrationRegistry.ts`

Rule:
`ARIA_GLOBAL_CORE` is the only runtime orchestration authority.

Verified sources currently include:
- Swarms canonical repo: `kyegomez/swarms`, Apache-2.0;
- Marketing Swarm Template, MIT;
- Multi-Agent Marketing Course, MIT;
- CrewAI, MIT;
- LangGraph, MIT;
- AutoGen reference-only because maintenance mode;
- ai-agents-101 is an n8n tutorial/reference rather than runtime;
- GitHub ai-marketing topic is discovery-only.

Swarms/CrewAI/LangGraph contribute patterns, not competing runtime authority.

## Updated exact continuation after observability

A fresh GPT should now:

1. Read issue #7 and this entire checkpoint.
2. Fetch the current ORDER-004 HEAD; do not assume the SHA above is still current.
3. Compare parent drift against ORDER-003 and record it.
4. Inspect at minimum:
   - packages/sniper/src/globalCore.ts
   - packages/sniper/src/cognition.ts
   - packages/sniper/src/operatingModel.ts
   - packages/sniper/src/commercialPolicy.ts
   - packages/sniper/src/telemetry.ts
   - packages/sniper/src/orchestrationRegistry.ts
   - packages/sniper/src/store.ts
   - apps/worker/src/index.ts
   - apps/cockpit/index.html
   - migrations/0003..0006
   - tests/sniper.test.mjs
5. Obtain a cloud-only $0 verification runner.
6. Run typecheck/tests/security/architecture/UI smoke.
7. Fix failures before claiming PASS.
8. Instrument specialist jobs, model calls, tool calls and effects with canonical spans.
9. Add a versioned SKILL REGISTRY.
10. Add DISCOVERY JOB and DEMO JOB contracts.
11. Connect audited procedural memory into Global Core scoring.
12. Implement semantic-memory support/contradiction/decay/supersession.
13. Only after the telemetry contract is stable, benchmark ONE external observability adapter from:
   - Laminar;
   - OpenLIT;
   - Observra.
14. Do not replace the product dashboard with a third-party observability UI.
15. Update this checkpoint before ending substantial work.

## Governed Skill Registry

Implemented:
- `packages/sniper/src/skillRegistry.ts`
- `migrations/0007_sniper_skill_registry.sql`
- `SniperStore.skillRegistryOverview()`
- `SniperStore.verifySkillSource()`
- GET `/api/sniper/skills`
- protected POST `/api/sniper/skills/verify`
- dashboard section `Skills`

Admission gates:
- source must be verified;
- license must be known;
- source artifact must be zero-cost;
- direct external-write permission is forbidden;
- SECRET data access is forbidden;
- exact revision pin is required;
- health must be verified;
- benchmark is required;
- benchmark threshold currently >= 0.60;
- secret-bound sources remain quarantined for dedicated review.

States:
- ENABLED
- QUARANTINED
- REJECTED

Important:
External source popularity never grants execution authority.

### First verified skill-source batch

Verified from upstream repositories:

1. `coreyhaines31/marketingskills`
   - MIT
   - Agent Skills spec compatible
   - CRO/copywriting/SEO/analytics/growth/attribution/pricing/sales enablement
   - source verified but currently UNPINNED / UNBENCHMARKED → QUARANTINED

2. `alirezarezvani/claude-skills`
   - MIT
   - very large cross-domain library
   - individual selection required; never enable wholesale
   - source verified but currently UNPINNED / UNBENCHMARKED → QUARANTINED

3. `ericosiu/ai-marketing-skills`
   - MIT
   - growth experiments/SEO/CRO/content/competitive analysis/decks
   - bundled scripts/dependencies require full-skill review
   - source verified but currently UNPINNED / UNBENCHMARKED → QUARANTINED

4. `aaron-he-zhu/aaron-marketing-skills`
   - Apache-2.0
   - 120 marketing skills with internal quality-gate patterns
   - source verified but currently UNPINNED / UNBENCHMARKED → QUARANTINED

5. `addyosmani/agent-skills`
   - MIT
   - spec/plan/build/TDD/review/web performance/ship gates
   - source verified but currently UNPINNED / UNBENCHMARKED → QUARANTINED

6. `emilkowalski/skills`
   - MIT
   - UI taste/animation/mobile-native/prototype/library selection
   - source verified but currently UNPINNED / UNBENCHMARKED → QUARANTINED

Do not mark any of these ENABLED until an exact commit/release is pinned and benchmark evidence is stored.

## Cloud verification status update

Rechecked after observability/skill work:

- Codex Tasks registered environments: none.
- Floot provides its own project VM/typecheck/tests, but does not execute this existing GitHub repository as-is.
- No user-PC execution is allowed.
- No paid hosted runner was enabled.

Therefore ORDER-004 remains:
`UNVERIFIED_CLOUD_RUNNER`

Do not claim typecheck/test PASS until a real cloud runner executes the current branch.

## Governed market discovery

Implemented:
- `packages/sniper/src/discovery.ts`
- `packages/sniper/src/discoverySources.ts`
- `migrations/0008_sniper_discovery.sql`
- durable source verification, jobs, findings and digital audits in `SniperStore`
- GET `/api/sniper/discovery/sources`
- GET `/api/sniper/discovery/jobs`
- protected POST `/api/sniper/discovery/source/verify`
- protected POST `/api/sniper/discovery/jobs`
- protected POST `/api/sniper/discovery/finding`
- dashboard section `Discovery`

Discovery invariant:
**crawler/source code license is NOT permission to automate a target source.**

Every source requires independent proof for:
- exact source revision;
- runtime cost = $0;
- target terms;
- automation permission;
- public-business-data scope;
- runtime health.

Current source candidates:

1. Firecrawl self-hosted
   - upstream active
   - AGPL-3.0
   - dedicated network-use license review required
   - hosted API is not assumed free
   - QUARANTINED

2. Crawl4AI self-hosted
   - upstream active
   - Apache-2.0
   - open-source self-host path is candidate
   - hosted cloud is pay-as-you-go and is NOT the zero-cost path
   - target automation terms not yet verified
   - QUARANTINED

3. Browser Use self-hosted
   - upstream active
   - MIT
   - self-host path may be a candidate
   - hosted Browser Use cloud is paid and is REJECTED for ORDER-003
   - target automation terms not yet verified
   - QUARANTINED

4. Scrapling self-hosted
   - upstream active
   - BSD-3-Clause
   - target automation terms not yet verified
   - QUARANTINED

No discovery source is currently ENABLED.

### Discovery job flow

`Global Core / operator goal → DiscoveryJob(locality,categories) → admitted source adapter → RawBusinessFinding → dedupe → DigitalAuditEvidence → BusinessSignal → SniperStore.ingest → CASE`

Rules:
- one business becomes one CASE;
- findings from multiple sources dedupe by domain/contact/name+locality;
- only published business contacts are eligible;
- no private personal phone/email enrichment;
- evidence refs remain attached;
- digital audit evidence drives website-quality/gap signals;
- named examples supplied in chat remain examples only, never hardcoded.

Current D1 tables:
- sniper_discovery_sources
- sniper_discovery_jobs
- sniper_discovery_findings
- sniper_digital_audits

The executor that performs real crawling/browser work is NOT connected yet.
Do not claim real Santa Fe market scanning is live until an admitted source adapter and cloud executor pass verification.

### Exact next continuation after discovery

1. Build Demo Job contract and private-preview lifecycle.
2. Keep heavy browser/build/3D execution outside normal Worker request execution.
3. Add cloud executor registry (Cloudflare lightweight / Oracle Free Tier heavy).
4. Add delivery transitions and acceptance.
5. Instrument discovery/demo execution with canonical telemetry.
6. Only then connect one admitted discovery adapter.
7. Continue to preserve no-PC and zero-spend invariants.
