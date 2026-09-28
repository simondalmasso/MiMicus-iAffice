# ORDER-004 CHECKPOINT — Autonomous Revenue Engine

Updated: 2026-09-28
Status: ACTIVE / IMPLEMENTED PARTIAL / NOT VERIFIED / NOT MERGE-READY

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
