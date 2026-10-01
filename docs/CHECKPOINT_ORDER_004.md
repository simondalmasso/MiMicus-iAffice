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
`simondalmasso/the-iAffice`

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

## Public deploy target

User-provisioned public Cloudflare Worker target:
- name: `agent-os`
- URL: `https://agent-os.simondalmasso44.workers.dev/`
- externally observed: HTTP 200, ~51 ms, currently plain-text placeholder rather than AriaOS cockpit/API.

Repository alignment:
- `wrangler.core.template.jsonc` public Worker name = `agent-os`
- `wrangler.template.jsonc` public Worker name = `agent-os`
- internal effect service remains `aria-effects`
- internal model service remains `aria-models`

Deploy order remains:
1. D1 migrations
2. `aria-effects`
3. `aria-models`
4. queues / Durable Objects / Workflow resources
5. `agent-os` public core + cockpit assets
6. live `/api/health` + UI smoke + reference gates

Do not treat the placeholder HTTP 200 as an application deploy PASS.

## CHECKPOINT REFRESH — 2026-09-30

Status remains:
`ACTIVE / IMPLEMENTED PARTIAL / UNVERIFIED_CLOUD_RUNNER / NOT MERGE-READY`

Reference HEAD immediately before this checkpoint refresh:
`bb4099c875cc3e00ae3906fe7995ad950cceb193`

Always fetch the live branch HEAD before continuing.

### Repository identity

Canonical repository is now:
`simondalmasso/the-iAffice`

Implementation branch:
`order-004-sniper-autonomous-revenue-engine-v1`

PR:
`#8 — DRAFT ORDER-004 — Autonomous Revenue Engine v1`

Stacked base remains:
`order-003-zero-cost-compute-market-v1@204ae12a74dd451561dc801631d671d35e65dd56`

Public product/package identity is moving to `iAffice`.
Internal capability boundaries intentionally remain `aria-models` and `aria-effects`.

### Public Cloudflare target

Public Worker:
`agent-os.simondalmasso44.workers.dev`

Repository config:
- public worker name = `agent-os`;
- cockpit assets = `apps/cockpit`;
- `aria-models` remains internal;
- `aria-effects` remains internal.

The public hostname was externally observed alive but serving the previous tiny placeholder.
Do NOT claim application deploy PASS until exact-head code is deployed and `/api/health` plus UI/API smoke pass.

### Cockpit repair

A real corruption was detected in `apps/cockpit/index.html` from cumulative remote edits:
- duplicated JavaScript after `</html>`;
- broken Telemetry function;
- malformed tail.

The file was rebuilt via Git Data in commit:
`d767460b5c749cafc973ca9a3698a6dfa372e61b`

Post-repair structural sanity:
- exactly one `<script>`;
- exactly one `</script>`;
- exactly one `</html>`;
- no content after `</html>`;
- one `renderTraceNodes`;
- one `demosView`;
- known corruption marker absent.

Current cockpit sections:
- Revenue
- Global Core
- Operations
- Discovery
- Demos
- Cases
- Live
- Decisions
- Learning
- Telemetry
- Skills
- Squad
- Approvals
- Compute
- System

Current branding in cockpit:
`iAffice · autonomous revenue operations`

### Demo Jobs are now durable and CASE-bound

Implemented:
- `packages/sniper/src/demoJobs.ts`
- `migrations/0009_sniper_demo_jobs.sql`
- store create/build/artifact/AUD lifecycle
- demos inside CASE dossier
- GET `/api/sniper/demos`
- protected POST `/api/sniper/demos`
- protected POST `/api/sniper/demos/artifacts`
- protected POST `/api/sniper/demos/audit`
- dashboard `Demos`

Flow:
`CASE → service pack → private demo job → cloud executor → artifact manifest → AUD → DEMO_READY`

Hard rules:
- demo is private;
- demo is never a production deploy;
- evidence is mandatory;
- executor must be verified zero-cost;
- AUD PASS is required before `DEMO_READY`.

### Cloud Executor Registry

Implemented:
- `packages/sniper/src/executorRegistry.ts`
- `migrations/0010_sniper_executor_registry.sql`
- durable executor verification
- GET `/api/sniper/executors`
- protected POST `/api/sniper/executors/verify`
- Demos dashboard shows executor admission.

Canonical candidates:

`CLOUDFLARE_CONTROL`
- CONTROL_PLANE only;
- owns canonical D1/control state;
- NOT a generic browser/filesystem/GPU sandbox.

`ORACLE_FREE_EXECUTOR`
- JOB_EXECUTOR candidate;
- capabilities: WEB_BUILD / BROWSER_3D / HEAVY_3D;
- user reports Oracle Free Tier is available;
- current state remains QUARANTINED because no enrolled/reachable executor endpoint has been verified from this environment.

SentinelX check at this checkpoint:
- no connected hosts;
- user Windows host is offline;
- Oracle is not enrolled/visible;
- user PC MUST NOT be used.

### Signed Executor Protocol

Implemented:
- `packages/sniper/src/executorProtocol.ts`
- `migrations/0011_sniper_executor_protocol.sql`

Allowed job kinds only:
- DISCOVERY_WEB_AUDIT
- DEMO_WEB_BUILD
- DEMO_BROWSER_3D
- DEMO_HEAVY_3D

There is NO arbitrary shell job kind.

Protocol properties:
- HMAC-SHA256 request envelope;
- protocol version `iaffice-executor-v1`;
- typed job kind;
- run id;
- job id;
- CASE id;
- SHA-256 payload digest;
- bounded artifact input refs;
- expected cost = 0;
- issued/expires timestamps;
- max TTL 15 minutes;
- nonce;
- safe HTTPS executor endpoint validation;
- localhost/private literal IP targets denied;
- credentials/query/fragment in executor endpoint denied;
- executor result validation;
- actual result cost MUST equal 0;
- artifact kinds are allowlisted;
- result telemetry is mandatory;
- executor results are HMAC-signed;
- final run can only be accepted once.

Durable run state:
`sniper_executor_runs`
now stores nonce, signed request envelope, expiry and result signature.

### Queue-driven executor dispatch

Implemented in `apps/worker/src/index.ts`.

When a demo is created and allowed:
1. it enters `QUEUED`;
2. core emits `{kind:"demo-dispatch", jobId}` to EVENTS_QUEUE;
3. Queue calls `prepareDemoExecutorRun()`;
4. store resolves the executor from durable registry;
5. caller-provided cost claims are ignored;
6. executor must be `ENABLED` and capability-compatible;
7. Core creates/reuses an idempotent signed run envelope;
8. Worker POSTs only to the registry-controlled HTTPS endpoint + fixed typed path;
9. accepted dispatch becomes `DISPATCHED`;
10. executor posts signed result to `/api/sniper/executor/result`;
11. signed callback bypasses admin-token auth but is authenticated by the dedicated HMAC secret;
12. successful result becomes demo artifacts → `AUDIT_REQUIRED`;
13. failed result becomes `FAILED`;
14. successful artifacts never become production automatically.

Runtime secret name:
`EXECUTOR_SIGNING_KEY`

It is documented in `.env.example` and must be installed as a secret/binding, never committed.

### Contextual relearning is connected to Global Core

Implemented:
`packages/sniper/src/learning.ts`

The previous fixed `auditedWinRate: 0` is removed.

Current behavior:
- audited WON/LOST episodes update procedural tactic statistics;
- audited WON/LOST episodes also update semantic patterns;
- patterns are scoped by category and by category+locality;
- semantic support and contradictions accumulate;
- unaudited observations do not mutate durable semantic memory;
- repeated support can promote CANDIDATE → VERIFIED;
- contradictions can demote to DISPUTED;
- smoothed outcome rates prevent one-shot overfitting;
- Global Core consumes category/locality historical outcome rate;
- no history = neutral prior 0.5;
- local context is used when support is sufficient, otherwise category prior is used.

This means:
**results/negotiations/audits now feed future company-level prioritization instead of remaining passive logs.**

### Current migrations

The migration chain is now:

- 0001_initial.sql
- 0002_compute_market.sql
- 0003_sniper_revenue_engine.sql
- 0004_sniper_cognitive_memory.sql
- 0005_sniper_global_core.sql
- 0006_sniper_observability.sql
- 0007_sniper_skill_registry.sql
- 0008_sniper_discovery.sql
- 0009_sniper_demo_jobs.sql
- 0010_sniper_executor_registry.sql
- 0011_sniper_executor_protocol.sql

### ORDER-004 doctor and UI smoke

`scripts/doctor.mjs` was rewritten for ORDER-004.

It now checks:
- Node >=22;
- lockfile;
- all migrations on an empty SQLite DB;
- current key tables;
- strict typecheck;
- cockpit structural integrity;
- current 15 cockpit sections;
- public worker target `agent-os`;
- private `aria-models` / `aria-effects` boundary;
- cron count;
- self-hosted CI cost guard;
- zero-spend source guards.

`scripts/ui_smoke_order004.py` now exists and checks desktop + mobile:
- iAffice branding;
- all 15 current sections;
- Demos;
- Oracle executor visibility;
- Telemetry;
- Compute $0 surface;
- navigation/accessibility basics.

These tests are PREPARED but NOT yet executed on a verified cloud runner.

### CI branch alignment

`.github/workflows/verify.yml` now targets:
- push: `order-004-sniper-autonomous-revenue-engine-v1`
- PR base: `order-003-zero-cost-compute-market-v1`

Runner remains:
`self-hosted`

This is deliberate. Do NOT silently switch to a potentially billable hosted runner.

Current missing piece:
a connected zero-cost cloud self-hosted runner, preferably the user's Oracle Free Tier.

### Deploy preparation

Added:
`scripts/render-deploy-config.mjs`

It renders generated Wrangler configs from templates using:
- `CLOUDFLARE_D1_DATABASE_ID`
- `ARIA_HEAD_SHA`

It does not persist or print secret values.

Generated target filenames:
- `.generated/wrangler.agent-os.jsonc`
- `.generated/wrangler.effects.jsonc`
- `.generated/wrangler.models.jsonc`

Package metadata now uses:
`name = iaffice`

`package-lock.json` is aligned to `iaffice`.

### Current verification truth

DO NOT claim PASS for:
- typecheck;
- npm test;
- coverage;
- security;
- architecture;
- ORDER-004 doctor;
- ORDER-004 Playwright smoke;
- Cloudflare exact-head deploy;
- live D1 migration;
- live service binding;
- live Oracle executor.

Reason:
there is still no connected zero-cost cloud runner / Cloudflare deployment credential path available through current tools.

This is a blocker, not a failure.

### Exact continuation for a fresh GPT

A fresh GPT must:

1. Read issue #7.
2. Read PR #8.
3. Read this entire checkpoint.
4. Fetch current branch HEAD; never trust the reference SHA above as current.
5. Compare ORDER-004 against ORDER-003 base and record drift.
6. Inspect:
   - `packages/sniper/src/engine.ts`
   - `packages/sniper/src/cognition.ts`
   - `packages/sniper/src/globalCore.ts`
   - `packages/sniper/src/learning.ts`
   - `packages/sniper/src/operatingModel.ts`
   - `packages/sniper/src/commercialPolicy.ts`
   - `packages/sniper/src/telemetry.ts`
   - `packages/sniper/src/skillRegistry.ts`
   - `packages/sniper/src/discovery.ts`
   - `packages/sniper/src/discoverySources.ts`
   - `packages/sniper/src/demoJobs.ts`
   - `packages/sniper/src/executorRegistry.ts`
   - `packages/sniper/src/executorProtocol.ts`
   - `packages/sniper/src/store.ts`
   - `apps/worker/src/index.ts`
   - `apps/cockpit/index.html`
   - migrations 0001..0011
   - `scripts/doctor.mjs`
   - `scripts/ui_smoke_order004.py`
7. Do NOT use Simon's PC.
8. First attempt to connect/enroll Oracle Free Tier as the zero-cost cloud runner/executor.
9. Once Oracle is reachable:
   - health-check it;
   - expose it through HTTPS;
   - verify actual zero-cost state/evidence;
   - persist executor verification;
   - set `EXECUTOR_SIGNING_KEY` securely on both ends;
   - keep Oracle stateless relative to canonical D1;
   - optionally register it as the GitHub self-hosted runner.
10. Run exact-head CI:
    - npm ci --offline --ignore-scripts
    - npm run typecheck
    - npm test
    - npm run test:coverage
    - npm run e2e
    - npm run e2e:compute
    - npm run benchmark
    - npm run benchmark:compute
    - npm run chaos:compute
    - npm run security
    - npm run doctor:004
    - python scripts/ui_smoke_order004.py
11. Fix every observed failure. Do not claim PASS from static inspection.
12. Only after deterministic cloud verification, prepare Cloudflare:
    - D1;
    - migrations 0001..0011;
    - queues/DLQ;
    - Durable Objects;
    - Workflow;
    - internal `aria-effects`;
    - internal `aria-models`;
    - public `agent-os` + cockpit assets;
    - secrets/bindings.
13. Deploy exact HEAD.
14. Verify:
    - `/api/health`
    - `/api/sniper/global`
    - `/api/sniper/operations`
    - `/api/sniper/discovery/*`
    - `/api/sniper/demos`
    - `/api/sniper/executors`
    - `/api/sniper/telemetry`
    - desktop/mobile cockpit.
15. Only after deploy gates pass, enable ONE real discovery adapter.
16. Keep real outreach/payment/deploy effects behind A1 policy/effect gateway.
17. Update this checkpoint in present tense before ending substantial work.

## CHECKPOINT REFRESH — 2026-09-30 18:40 ART

Present state:
`ACTIVE / IMPLEMENTED PARTIAL / CLOUD VERIFICATION BLOCKED / PRODUCTION NOT DEPLOYED / DO NOT MERGE`

Exact branch HEAD at checkpoint creation:
`caae98096e4cf84d803a59009209e586d040ba88`

Repository:
`simondalmasso/the-iAffice`

Branch:
`order-004-sniper-autonomous-revenue-engine-v1`

PR:
`#8 — DRAFT ORDER-004 — iAffice Autonomous Revenue OS v1`

Stacked base remains:
`order-003-zero-cost-compute-market-v1@204ae12a74dd451561dc801631d671d35e65dd56`

Always fetch the live HEAD before continuing. Never assume the SHA above is still current.

### Repository is currently organized around one canonical path

Canonical docs:
- `README.md`
- `AGENTS.md`
- `docs/REPO_MAP.md`
- `docs/CHECKPOINT_ORDER_004.md`
- `docs/DEPLOYMENT.md`
- `docs/ORACLE_EXECUTOR_RUNBOOK.md`

Canonical Wrangler templates:
- `wrangler.core.template.jsonc`
- `wrangler.models.template.jsonc`
- `wrangler.effects.template.jsonc`

The duplicate generic `wrangler.template.jsonc` is removed.

Generated deployment configs live only under:
`.generated/`

`scripts/render-wrangler.mjs` remains only as a deprecated compatibility wrapper.
Canonical renderer:
`scripts/render-deploy-config.mjs`

The unused/conflicting `packages/sniper/src/semanticMemory.ts` is removed.
Canonical durable semantic/procedural learning is:
- `packages/sniper/src/learning.ts`
- `sniper_semantic_patterns`
- audited `sniper_memory_episodes`
- `sniper_tactic_learning`

### Current migration chain is 0001..0012

Current migrations:
- 0001_initial.sql
- 0002_compute_market.sql
- 0003_sniper_revenue_engine.sql
- 0004_sniper_cognitive_memory.sql
- 0005_sniper_global_core.sql
- 0006_sniper_observability.sql
- 0007_sniper_skill_registry.sql
- 0008_sniper_discovery.sql
- 0009_sniper_demo_jobs.sql
- 0010_sniper_executor_registry.sql
- 0011_sniper_executor_protocol.sql
- 0012_sniper_commercial_guard.sql

Migration 0012 adds:
- `sniper_contact_controls`
- `sniper_commercial_effects`

No production migration 0012 is applied yet because the current public Worker is still the placeholder.

### Audited memory replay is now idempotent

`SniperStore.recordEpisode()` first checks `episode_id`.

Behavior:
- identical replay returns `idempotent=true`;
- conflicting replay throws `SNIPER_EPISODE_REPLAY_CONFLICT`;
- an already-recorded episode does NOT increment tactic or semantic memory again.

This prevents Queue/retry duplication from biasing learned tactics and portfolio priorities.

### Commercial safety is now a real double gate

Previous state:
`commercialPolicy.ts` existed but was disconnected.

Current state:
the commercial policy is enforced in both control plane and effect gateway.

Files:
- `packages/sniper/src/commercialPolicy.ts`
- `packages/sniper/src/commercialGuard.ts`
- `apps/worker/src/index.ts`
- `apps/effects-worker/src/index.ts`
- `migrations/0012_sniper_commercial_guard.sql`

Persuasive outreach means:
- SEND_OUTREACH
- SCHEDULE_EXTERNAL_MEETING
- SEND_PROPOSAL

Current persuasive limits:
- max 3 autonomous persuasive contacts per rolling 30-day window;
- minimum 48 hours between persuasive contacts;
- public/owner-provided business contact provenance only;
- durable opt-out / explicit refusal;
- no bulk blast;
- no unsupported claim;
- no false urgency;
- no human impersonation;
- exact-payload commercial AUD PASS required.

Transactional SEND_DELIVERY_NOTICE / SEND_RECEIPT is separated from marketing fatigue/opt-out logic.
SEND_RECEIPT still requires verified payment.

Commercial state is derived from D1, not from a model assertion:
- contact provenance from CASE contacts;
- opt-out/refusal from `sniper_contact_controls`;
- contact count/cooldown from executed `sniper_commercial_effects`;
- accepted offer from CASE/negotiation state;
- delivery approval from delivery acceptance;
- payment verification from payment state;
- HUMAN_GATE from the latest negotiation;
- copy audit from canonical `audit_findings`.

Exact-payload audit:
`commercialActionDigest(caseId, operation, target, payload)`

Persuasive action requires a canonical audit:
- target_id = exact commercial payload digest;
- verdict = PASS;
- strategy = `COMMERCIAL_COPY_GUARD`;
- evidence refs non-empty.

Protected internal APIs now include:
- POST `/api/sniper/contact-control`
- POST `/api/sniper/commercial/audit`
- POST `/api/sniper/commercial/action`

`/api/sniper/commercial/action`:
1. validates typed operation;
2. evaluates current D1 commercial state;
3. returns 409 for HUMAN_GATE;
4. returns 403 for policy denial;
5. derives ActionClass from the operation;
6. refuses operations with no real effect adapter;
7. creates an exact-digest ActionIntent;
8. creates action-bound approval;
9. persists the commercial metadata inside the action digest.

The generic `/api/actions/request` rejects CASE-linked external actions with:
`CASE_EXTERNAL_ACTION_REQUIRES_COMMERCIAL_GATE`

This prevents the generic endpoint from bypassing CASE commercial policy.

### aria-effects now revalidates commercial policy after approval

For an external ActionIntent whose subject is an existing CASE:
- commercial metadata is mandatory;
- ExternalOperation → ActionClass is checked again;
- current D1 commercial guard is reevaluated;
- HUMAN_GATE blocks;
- changed opt-out/refusal blocks;
- changed contact fatigue/cooldown blocks;
- changed acceptance/payment state blocks;
- changed/missing audit blocks;
- changed payload digest blocks.

Only after EffectKernel returns EXECUTED:
`CommercialGuard.recordExecuted()`
writes durable effect history.

Therefore:
**an old human approval does not override a newer opt-out, cooldown, HUMAN_GATE or payload mutation.**

Current `safe-outbound` adapter is still simulated.
It unwraps the commercial envelope and stores only the outbound payload.

Real email / WhatsApp / payment / publish / customer-deploy adapters are NOT connected yet.
Unsupported commercial operations fail closed with:
`COMMERCIAL_EFFECT_ADAPTER_NOT_AVAILABLE`

Global policy still denies money/credential mutation where previously defined.
Do not claim autonomous payment/invoice/credential transfer is live.

### CASE dossier now exposes commercial safety

CASE API/dashboard now shows:
- DO NOT CONTACT state;
- explicit refusal;
- contact-control evidence;
- recent executed commercial effects;
- existing negotiation HUMAN_GATE.

The cockpit labels commercial safety as revalidated again inside `aria-effects`.

### Commercial guard tests now include real migrations

`tests/sniper.test.mjs` now has:
- public contact provenance tests;
- exact commercial payload digest tests;
- transaction vs marketing policy tests;
- real `node:sqlite` D1 adapter;
- all migrations applied to in-memory SQLite;
- AUD-passed outreach → ALLOW;
- opt-out after audit → DENY;
- executed contact + short interval → CONTACT_COOLDOWN;
- current negotiation human gate + proposal → HUMAN_GATE.

These tests are written but NOT yet executed on an authorized Oracle runner.

### Doctor now requires the commercial double gate

`scripts/doctor.mjs` now expects >=12 migrations and tables:
- `sniper_contact_controls`
- `sniper_commercial_effects`

It also statically requires:
- Core `CommercialGuard`;
- `/api/sniper/commercial/action`;
- generic CASE external-action bypass rejection;
- aria-effects commercial revalidation;
- payload digest revalidation;
- executed-effect recording;
- core commercial rules.

This is prepared evidence, NOT a PASS result until executed.

### Oracle executor now accepts jobs asynchronously

The previous executor request path could block until a build finished.
That is no longer true.

Current `apps/oracle-executor/iaffice_executor.py`:
- validates signed envelope;
- persists runId/nonce before execution;
- responds HTTP 202 quickly;
- runs the typed job in a background thread;
- does not duplicate an already-running run;
- persists signed result before callback;
- tracks callback state/attempts/error;
- retries callback with backoff;
- scans pending callbacks after restart every ~5 minutes;
- continues to expose NO arbitrary-shell job type;
- continues to keep Discovery web audit disabled/fail-closed.

Private artifact HMAC/digest proxy remains in place.

### Verification tooling is runner-reproducible

Added:
`scripts/bootstrap_verify_tools.sh`

Pinned defaults:
- TypeScript 5.9.3
- Playwright 1.55.0

It installs Playwright Chromium for the cloud runner.
`scripts/ui_smoke_order004.py` no longer hardcodes `/usr/bin/chromium`.

### GitHub Actions is deliberately manual-only now

`.github/workflows/verify.yml`:
- workflow_dispatch only;
- exact ORDER-004 branch;
- runner labels:
  `[self-hosted, linux, oracle-free, iaffice]`
- bootstraps pinned verification tools;
- executes the full exact-head ORDER-004 gate.

This prevents Simon's Windows host or a GitHub hosted runner from receiving ORDER-004 work.

Old run:
- workflow run #78
- run id 36777859725
- job id 110100217350
- state observed: queued
- belongs to an older HEAD;
- it is stale;
- current GitHub connector exposes no cancel-run operation.

Ignore this run as validation evidence.

### Production deploy workflow exists but cannot run yet

`.github/workflows/deploy-production.yml` is manual-only.

It requires explicit input:
`DEPLOY_AGENT_OS`

It is Oracle-only and requires GitHub production secrets:
- CLOUDFLARE_API_TOKEN
- CLOUDFLARE_ACCOUNT_ID
- CLOUDFLARE_D1_DATABASE_ID
- ADMIN_TOKEN_HASH
- APPROVAL_SIGNING_KEY
- WEBHOOK_SECRET
- EXECUTOR_SIGNING_KEY

It:
1. enforces exact branch HEAD;
2. verifies required secret presence without printing values;
3. runs full ORDER-004 verification;
4. runs deploy preflight;
5. renders generated Wrangler configs;
6. installs core secrets;
7. runs canonical Cloudflare deployment;
8. runs exact-head live acceptance.

The available GitHub connector cannot dispatch workflow_dispatch.
No deploy was triggered from this chat.

### Cloudflare deploy path is now canonical and less ambiguous

`scripts/cloudflare-preflight.mjs`:
- requires Cloudflare deploy token + account id;
- does NOT require external Groq/Mistral/Gemini credentials just to deploy the app;
- verifies worker boundary topology;
- rejects configured paid model IDs.

`scripts/ensure-cloudflare-resources.sh`:
- verifies the supplied D1 ID exists;
- verifies it is the existing `ariaos-v1` database;
- does NOT silently create a different D1;
- ensures Queue `ariaos-events-v1`;
- ensures DLQ `ariaos-events-v1-dlq`;
- creates only missing queues.

`scripts/deploy-cloudflare.sh`:
`exact HEAD → preflight → render → D1/Queue check → migrations → aria-models → aria-effects → agent-os`

`scripts/live_acceptance_order004.py` checks exact SHA, real cockpit HTML, core APIs and security headers.

### Production truth at this checkpoint

Observed live:
`https://agent-os.simondalmasso44.workers.dev/`

Observed:
- HTTP 200;
- response is still 12-byte `text/plain` placeholder;
- `/api/health` returns the same placeholder behavior;
- current app/API is NOT deployed;
- current security headers from the new Worker code are therefore NOT live.

Deployment state:
`BLOCKED_REAL_CLOUDFLARE_CREDENTIAL_PATH + ORACLE_RUNNER_NOT_ENROLLED`

No Cloudflare connector is available in current tools.
No OCI connector is available.
SentinelX reports no connected hosts/integrations.
No Simon-PC fallback is permitted.

### Hourly continuity is active

An hourly continuation task is active.

Every run is instructed to:
- resume ORDER-004 without reset;
- fetch exact current HEAD;
- read issue #7 / PR #8 / AGENTS / REPO_MAP / checkpoint;
- never use Simon's PC;
- continue safe pending code if deploy remains blocked;
- never fabricate PASS;
- preserve zero-spend/A1 boundaries;
- update this checkpoint in present tense before ending.

### Exact continuation for a fresh GPT

A fresh GPT must execute this sequence:

1. Read issue #7.
2. Read PR #8.
3. Read `AGENTS.md`.
4. Read `docs/REPO_MAP.md`.
5. Read this checkpoint, especially the newest refresh.
6. Fetch live HEAD of:
   `order-004-sniper-autonomous-revenue-engine-v1`.
7. Confirm PR base still:
   `order-003-zero-cost-compute-market-v1@204ae12a74dd451561dc801631d671d35e65dd56`.
8. Do not reset/rebase to main.
9. Do not use Simon's PC.

First infrastructure priority:
10. Obtain authorized shell on the existing Oracle Free Tier target using the existing ORDER076 path only.
11. Confirm expected host identity before mutation.
12. Checkout exact current ORDER-004 branch under a dedicated cloud path.
13. Run:
    `python3 scripts/oracle_executor_selftest.py`
14. Install executor only if self-test passes.
15. Bootstrap GitHub self-hosted runner with labels:
    `oracle-free,iaffice`
16. Do not create another SSH key or control plane.

Verification priority:
17. Manually dispatch `order-004-zero-cost-self-hosted-verify` from the ORDER-004 branch once Oracle runner is online.
18. Require exact HEAD.
19. Run the entire suite and repair every observed failure.
20. Do not use static inspection as PASS evidence.

Deployment priority after exact-head PASS:
21. Ensure GitHub production secrets exist without exposing values.
22. Manually dispatch `order-004-production-deploy` with:
    `DEPLOY_AGENT_OS`
23. The workflow must verify existing D1 and queues, apply migrations 0001..0012, deploy internal workers, then `agent-os`.
24. Run `scripts/live_acceptance_order004.py`.
25. Confirm root is real iAffice HTML and `/api/health` reports exact SHA.

Oracle executor after Core is live:
26. Configure the same EXECUTOR_SIGNING_KEY on Oracle.
27. Put Oracle behind an authorized stable HTTPS hostname.
28. Start executor and check localhost + public health.
29. Gather real free-tier evidence for this exact VM.
30. POST protected `/api/sniper/executors/verify`.
31. Require Oracle admission = ENABLED.
32. Run one private demo:
    `CASE → Demo Job → Queue → Oracle → signed result → private artifact → AUD`.
33. Verify private artifact proxy digest and auth.

Commercial acceptance after deployment:
34. Create a test CASE using only synthetic/test contact data.
35. Create exact-payload commercial AUD PASS.
36. Create commercial action.
37. Verify approval is action-bound.
38. Before approving, set DO NOT CONTACT and prove aria-effects rejects the stale approval.
39. Clear only in a separate test CASE; verify cooldown after one executed simulated safe-outbound effect.
40. Do not connect real outbound email/WhatsApp until a legitimate authorized adapter and its own compliance/cost gates exist.

Only after all above:
41. consider enabling ONE discovery adapter;
42. then add one real outbound connector;
43. then payment/deploy adapters;
44. preserve HUMAN_GATE for large/meeting/non-standard/legal cases;
45. keep actual production/customer deployment behind action-bound approval.

Current forbidden claims:
- do not say ORDER-004 tests PASS;
- do not say Oracle runner is online;
- do not say Oracle executor is live;
- do not say Cloudflare app is deployed;
- do not say outbound email/WhatsApp is live;
- do not say Mercado Pago/invoicing is live;
- do not say Discovery is scanning Santa Fe live;
- do not merge PR #8.


## Continuation refresh — 2026-09-30 22:23 ART

Verified from live GitHub state: branch HEAD remains `62c3ba5ed2d23c3574fb301569c4abcca9ca38ec`; PR #8 remains draft and stacked on `order-003-zero-cost-compute-market-v1@204ae12a74dd451561dc801631d671d35e65dd56`. No cloud-runner PASS is claimed.

Prepared but blocked by repository-write safety enforcement in this run: raise executor HMAC signing-key minimum from 8 characters to at least 32 UTF-8 bytes on TypeScript and Python boundaries; align Python Discovery target validation with the existing TypeScript rejection of localhost/private literal IPv4 targets and URL credentials; update self-test fixtures and deterministic regression coverage. Discovery remains disabled/fail-closed, so this mismatch is not represented as an enabled live SSRF path.

Current blocked state remains `ORACLE_RUNNER_NOT_ENROLLED + BLOCKED_REAL_CLOUDFLARE_CREDENTIAL_PATH`. No deploy, spend, outreach, charge, publish, merge, infrastructure creation, or Simon-PC execution occurs in this run.

Exact continuation: re-read live HEAD before mutation; apply the narrowly scoped executor hardening above if still absent; run the full ORDER-004 suite only on the authorized Oracle Free Tier runner and claim PASS only from exact-HEAD execution; keep Discovery disabled until target validation is aligned and tested; keep D1 canonical, aria-models isolated, aria-effects as the protected business-write boundary, and zero-spend fail-closed.


## Continuation refresh — 2026-10-01

Live branch HEAD inspected before this refresh: `d85753562f5990afdcbfcb9ddc3b678233289011`. PR #8 remains draft and stacked on ORDER-003 base `204ae12a74dd451561dc801631d671d35e65dd56`; no reset/rebase is performed.

Verified by static inspection in this run:
- D1 remains canonical; `aria-models` remains isolated; `aria-effects` remains the protected business-write boundary.
- Oracle executor exposes typed job paths only; no arbitrary-shell API exists.
- Discovery execution remains disabled/fail-closed with `DISCOVERY_EXECUTOR_ADAPTER_NOT_ENABLED`.
- Executor signing-key validation is still weaker than intended: TypeScript and Python accept keys shorter than 32 UTF-8 bytes.
- Python Discovery target validation is weaker than TypeScript and currently accepts generic http/https targets without equivalent localhost/private-literal/credential rejection.
- No registered Codex cloud execution environment is available, so no cloud test PASS is claimed.

Prepared but blocked:
- Change TypeScript and Python signing-key admission to require at least 32 UTF-8 bytes.
- Bring Python Discovery target validation into parity with the TypeScript public-web target boundary.
- Update Oracle self-test fixtures and deterministic regressions for short keys/private targets.
- Direct repository mutation of those executor files is blocked by the active connector safety enforcement in this run; do not represent the patch as applied.

Exact continuation for a fresh GPT:
1. Fetch the live HEAD again; do not assume the SHA above remains current.
2. Re-read issue #7, PR #8, AGENTS.md, REPO_MAP and this checkpoint; preserve the ORDER-003 stacked base.
3. Apply only the narrow executor hardening above if repository writes are available; do not enable Discovery while Python validation remains weaker.
4. Run exact-HEAD verification only on an authorized zero-cost cloud runner. Never use Simon's PC and never substitute a potentially billable hosted runner.
5. Keep Oracle non-canonical, zero-spend fail-closed, and typed-only; do not add a shell/command executor.
6. Do not deploy, spend, send outreach, charge, publish, merge or create infrastructure without the existing explicit gates and credentials.
7. Update this checkpoint again before ending the next substantial run.
