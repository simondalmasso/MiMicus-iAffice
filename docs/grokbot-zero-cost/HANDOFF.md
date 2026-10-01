# GROKBOT HANDOFF — Mimicus $0 Architecture Challenge

## Role

You are an independent architecture worker for **Mimicus iAffice**.

Your job is to inspect the repository, verify the current state, research alternatives, and propose the strongest practical **$0 architecture** for Mimicus without replacing its orchestration core.

You are NOT the integration owner. Your output will later be audited, corrected, refined, and selectively integrated by the Mimicus AUD/ARQ worker.

## Repository and branch contract

Repository:
https://github.com/simondalmasso/the-iAffice

YOUR ONLY WRITE BRANCH:
`grokbot/mimicus-zero-cost-architecture`

This branch was created from:
`mimicus-v2-monochrome@f9d185203e5ab9362a56dda2dcd7fd38e39db22f`

Push all of your work ONLY to:
`grokbot/mimicus-zero-cost-architecture`

Do not push to:
- `main`
- `mimicus-v2-monochrome`
- any setter branch
- any AUD/ARQ branch you discover

Do not merge anything.
Do not mark PR #9 ready.
Do not deploy production.
Do not delete repositories, branches, source history, evidence, or archives.

## Parallel work already in progress

Other workers are active simultaneously in the same repository/project:

1. **Mimicus AUD/ARQ** — architecture/audit/integration owner.
2. **Facebook Setter** — independent Facebook setter workstream.
3. **Reddit Setter** — independent Reddit setter workstream.
4. **You / Grokbot** — isolated $0 architecture proposal.

Assume concurrent commits may appear elsewhere while you work.

Your mutable ownership is intentionally isolated.

### Paths you MAY own

Prefer creating new files only under:

`docs/grokbot-zero-cost/`

and, only if a proof of concept is truly necessary:

`experiments/grokbot-zero-cost/`

### Paths you MUST NOT modify

Do not modify shared product/integration surfaces, including:
- `README.md`
- `worker.js`
- `wrangler.toml`
- `package.json`
- `public/**`
- `HANDOFF-SETTER-FACEBOOK.md`
- `HANDOFF-SETTER-REDDIT.md`
- `SETTERS.md`
- `data/gpt-prospectos.json`
- `archive/MiMicus-swarm-source/**`
- `evidence/**`
- existing GitHub workflows

If you believe one of those files must change, document the proposed diff in your architecture report instead of changing it.

## Current product state

Product: **Mimicus iAffice**

Current active product branch:
`mimicus-v2-monochrome`

Known product HEAD at your branch point:
`f9d185203e5ab9362a56dda2dcd7fd38e39db22f`

Current draft PR:
https://github.com/simondalmasso/the-iAffice/pull/9

PR #9 is intentionally DRAFT / NO MERGE.

Known deployment:
https://mimicus.simondalmasso44.workers.dev

Known Cloudflare Worker Version ID:
`8840605b-6249-498c-8c78-fbc434405dc9`

Known live evidence at the branch point:
- root HTTP 200
- `/api/health` reports `ok=true`
- service = `mimicus`
- ui = `monochrome-v2`

Visual identity is canonical:
- grayscale / black monochrome
- LAYA central supervisor
- visible agent network
- extremely slow/smooth motion
- living Activity Stream at the bottom
- do not redesign the visual identity as part of this task

V1 is **simulation-safe**.
External side effects remain OFF by default.

## Existing absorbed source and verified provenance

Original source repository:
https://github.com/simondalmasso/MiMicus-swarm

Canonical source branch:
`order-002-mimicus-v01`

Exact source HEAD:
`565407eb1296eae617f5b14b512d2e0cf08c6c02`

The source has already been absorbed non-squashed into:

`archive/MiMicus-swarm-source/`

Verified facts before your task began:
- exact source commit exists in both repositories
- the target repository contains the source commit in its ancestry
- subtree merge commit:
  `038ce795f16d193bb31a9308435724f6d73822eb`
- subtree split:
  `565407eb1296eae617f5b14b512d2e0cf08c6c02`
- source blobs compared with archive at current Mimicus HEAD:
  - source blobs: 311
  - archive blobs: 311
  - missing: 0
  - extra: 0
  - SHA/mode mismatches: 0

A literal fresh shell clone was NOT completed because the prior execution shell had DNS/network resolution failure. Therefore do not claim that final fresh-clone verification is complete unless you personally reproduce it.

Do NOT propose deleting `MiMicus-swarm` until a clean fresh clone and archive verification is independently demonstrated.

## Existing Mimicus architecture — invariants you must preserve

The absorbed source contains a mature orchestration core.

Canonical architectural principles:
- **LAYA is the supervisor / control plane**
- one orchestration control plane
- bounded coalitions
- morphologies:
  - `solo`
  - `paired_verify`
  - `parallel_fanout`
  - `sparse_graph`
  - `hierarchical_fanout_fanin`
- provenance/evidence is first-class
- falsification/verification is first-class
- governed memory
- no authority expansion by adapters/plugins
- explicit effect boundaries
- simulation-safe by default

Core engine:
- `MiMicusEngine`
- canonical execution plan is a hashable Morphology DAG
- `DagExecutor` schedules ready nodes with bounded concurrency
- cancellation and replay/determinism concepts exist
- exact agent fingerprints/provenance exist
- budget ledger exists
- falsifier market exists
- immutable evidence structures exist
- sparse communication uses bounded challenge objects
- no raw hidden chain-of-thought sharing
- germinal learning mechanisms exist
- arbitrary generated-code execution is NOT part of the core

Memory authority model:
- authority is policy, not vector similarity score
- lifecycle includes candidate/quarantined/private_verified/shared_verified/rejected/expired
- write/promotion/retrieval/cross-agent gates exist
- an external vector or graph database MUST NOT decide memory authority

Current Python source project:
- package: `mimicus-swarm`
- version: 0.2.2
- Python >=3.12,<3.15
- includes:
  - `openai-agents==0.21.1`
  - `pydantic==2.13.4`
  - SQLAlchemy / Alembic
  - MCP
  - pytest / pytest-cov / mypy / ruff
- test coverage gate: 90%

Existing extension seams include service protocols / adapters for:
- storage
- provider
- agent factory
- falsifiers
- memory
- coalition
- communication
- sandbox
- telemetry

Existing implementations include:
- `LocalSandboxService` with allowlisted primitives
- `LedgerTelemetryService`
- governed memory service
- coalition service
- sparse communication service

There is already an internal benchmark/replay/evidence system. Do not assume a third-party evaluation framework automatically adds net capability.

## Active Worker shell

The currently deployed web product is intentionally much smaller than the archived Python core.

Top-level active product currently includes approximately:
- `.github`
- `README.md`
- `archive`
- `docs`
- `evidence`
- `package.json`
- `public`
- `worker.js`
- `wrangler.toml`

Current Worker behavior:
- Cloudflare Worker + static assets
- `/api/health`
- `/api/runtime`
- static UI otherwise
- no declared runtime dependencies in current `package.json`
- external effects OFF

Your architecture must explicitly distinguish:
1. current Worker cockpit / UI runtime,
2. absorbed Python orchestration core,
3. future optional execution backends,
4. what can realistically run at $0.

Do not hand-wave this deployment boundary.

## Definition of "$0"

Design for **zero mandatory monetary cost** for local development, testing, evaluation, and a usable baseline runtime.

Rules:
- prefer open-source / locally executable components
- prefer current free infrastructure already in use when practical
- no architecture that requires a paid SaaS subscription
- no architecture whose core stops working when a free trial/free quota expires
- free tiers may be OPTIONAL accelerators, never mandatory foundations
- every external paid/freemium component must have a zero-cost fallback
- label variable LLM/API inference cost explicitly; do not call it "$0" if it depends on paid tokens
- distinguish "$0 software/infrastructure" from "$0 inference"
- avoid unnecessary databases, control planes, queues, or observability stacks
- minimize idle services and operational complexity
- licenses matter: do not copy code without a compatible explicit license

## Candidates already considered — re-verify independently

These are hypotheses / prior research, NOT instructions to adopt them.

### Open Dot — composio-community/open-dot

Potential useful patterns:
- action risk rules: allow / ask / never
- human takeover
- one abstraction across cloud/docker/local computers
- trigger/integration patterns

Prior concern:
- no explicit LICENSE was observed in the repository during prior review.

Therefore:
- independently verify current license
- do not copy code if license is absent/unclear
- ideas/patterns may be independently reimplemented

### Nace / Drex

Interesting as a constrained decision model that can return probabilities over supplied options.

Possible role:
- OPTIONAL `DecisionProvider`
- benchmark against existing Mimicus selector/routing

Constraints:
- no core authority
- no mandatory dependency
- prove measurable benefit
- independently verify price, license, self-host status, and availability

### Graphiti / Zep

Potential unique value:
- temporal / bi-temporal knowledge graph retrieval
- hybrid graph/semantic retrieval

Constraint:
- may be subordinate retrieval/index layer only
- MUST NOT become memory authority
- justify graph DB/embedding operational cost and complexity
- defer if current memory system already meets real requirements

### Langfuse

Potential value:
- tracing / observability / evaluation dashboards
- possible OpenTelemetry integration

Possible role:
- optional telemetry/export backend

Constraint:
- canonical evidence/provenance remains inside Mimicus
- product must work without Langfuse
- local/open-source path preferred

### DeepEval

Potential value:
- standardized LLM/agent evaluation
- trajectory/component evaluation
- pytest integration

Possible role:
- dev/eval-only dependency
- consume Mimicus provenance/evidence
- do not become runtime orchestration

Prefer deterministic/no-paid-model tests where possible.

### Browser Use

Potential value:
- browser automation/session patterns

Constraint:
- do NOT embed another autonomous agent/control loop as Mimicus core
- browser should be an actuator/tool under Mimicus DAG + effect policy
- compare against plain Playwright before adding another framework

### E2B

Potential value:
- isolated cloud sandbox primitive

Possible role:
- optional `SandboxService` backend

Constraint:
- local/Docker baseline first
- must not be mandatory for $0
- all effect boundaries remain explicit

### General agent frameworks

Already considered:
- LangGraph
- CrewAI
- AutoGen
- PydanticAI
- Dify
- Mastra
- Agno / AgentOS
- Semantic Kernel

Prior architectural hypothesis:
most are redundant if adopted as control planes because Mimicus already has:
- a supervisor
- DAG execution
- morphologies
- memory policy
- falsification
- evidence
- replay
- provider abstraction
- sandbox and telemetry seams

Do NOT add one merely because it is popular.

If any one has a uniquely separable primitive worth absorbing, identify the primitive and show how to implement/adapt it without replacing `MiMicusEngine`.

Note:
Mimicus already depends on Pydantic and OpenAI Agents in the absorbed Python core.

## InsForge

Do not add InsForge by default.

No current active Mimicus configuration/SDK use has been established.

Only recommend it if you can show a concrete missing capability that:
1. Mimicus actually needs,
2. cannot be solved more simply,
3. preserves $0 baseline,
4. does not duplicate existing storage/auth/runtime capabilities.

## Your mission

Produce a full architecture proposal answering:

**What is the maximum useful Mimicus architecture we can build at mandatory cost $0, while preserving LAYA/MiMicusEngine as the single control plane and avoiding redundant frameworks?**

You must research current facts rather than relying on old model memory.

For every external dependency you recommend, verify:
- current repository/project status
- exact license
- latest stable version or relevant version
- local/self-host viability
- actual free-tier limitations where applicable
- whether a paid account/card is required
- runtime/resource cost
- maintenance activity
- security/effect implications
- whether the capability already exists inside Mimicus

Prefer primary sources:
- official repository
- official docs
- official pricing
- official license
- official release notes

## Required architecture analysis

Evaluate at minimum:

1. Control plane
2. Execution DAG / scheduler
3. Provider/model routing
4. Decision/routing abstraction
5. Memory + retrieval
6. Temporal knowledge
7. Provenance/evidence
8. Telemetry/observability
9. Evaluations
10. Browser actuator
11. Sandbox/code execution
12. Human approval/effect policy
13. MCP/tool integration
14. Persistence
15. Cloudflare Worker boundary
16. Local development
17. replay/determinism
18. security model
19. deployment topology
20. cost model
21. failure/degradation modes
22. future migration strategy

For each subsystem classify:
- KEEP AS-IS
- REFACTOR INTERNAL
- OPTIONAL ADAPTER
- EXPERIMENT ONLY
- REJECT / REDUNDANT
- DEFER

## Mandatory architecture rules

1. LAYA / MiMicusEngine remains the only orchestration authority.
2. No nested swarm framework.
3. No second control plane.
4. External adapters cannot promote their own authority.
5. Memory policy remains canonical.
6. Evidence/provenance remains canonical.
7. Effects OFF by default.
8. Human approval gates for future external effects.
9. Zero-cost baseline must survive with all optional SaaS disabled.
10. All optional components must be removable.
11. Avoid vendor lock-in.
12. No code copy from unclear licenses.
13. No production deployment from your branch.
14. No merge to shared branches.
15. VERIFY > ASSUME.

## Strong candidate target shape to challenge, not blindly accept

A plausible architecture to test is:

- existing MiMicusEngine + Morphology DAG remain canonical
- evolve `LedgerTelemetryService` into a richer telemetry protocol
- retain local canonical ledger
- optional OpenTelemetry exporter
- optional Langfuse-compatible backend
- preserve `LocalSandboxService`
- add sandbox interface backends only when justified:
  - local baseline
  - Docker optional
  - E2B optional
- add Browser actuator behind effect receipts/approval policy:
  - Playwright baseline
  - Browser Use only if it adds measurable value without owning orchestration
- DeepEval only as development/evaluation adapter
- optional `DecisionProvider` experiment for Drex-like constrained selection
- Graphiti only if temporal graph retrieval wins a real benchmark
- reject general orchestration frameworks as core dependencies

Your job is to challenge this shape and improve it with evidence.

## Required deliverables

Commit and push the following to YOUR branch.

### 1. Architecture report

`docs/grokbot-zero-cost/ARCHITECTURE.md`

Must include:
- executive architecture
- component diagram
- data/control flow
- trust/authority boundaries
- effect boundary model
- deployment topology
- $0 baseline topology
- optional upgrade topology
- what stays canonical
- what is adapter-only
- what is rejected
- migration phases
- operational risks
- unresolved questions

Use Mermaid diagrams where useful.

### 2. Capability matrix

`docs/grokbot-zero-cost/CAPABILITY-MATRIX.md`

Columns:
- capability
- already in Mimicus?
- candidate
- net-new value
- overlap
- mandatory cost
- optional cost
- license
- local/self-host?
- complexity
- security/effect risk
- verdict
- evidence/source

Do not use vague ratings. Explain factual tradeoffs.

### 3. Cost model

`docs/grokbot-zero-cost/COST-MODEL.md`

Explicitly separate:
- software licensing
- hosting
- databases
- observability
- browser/sandbox
- model inference
- CI
- storage
- bandwidth

Show what is actually $0 and under what limits.

### 4. Integration plan

`docs/grokbot-zero-cost/INTEGRATION-PLAN.md`

Design an integration order that minimizes risk and merge collisions.

Every phase must include:
- owned paths
- API/interface touched
- dependency added
- feature flag/default
- acceptance test
- rollback
- cost impact
- authority impact

### 5. Evidence log

`docs/grokbot-zero-cost/EVIDENCE.md`

For every important external claim record:
- URL
- source type
- date checked
- exact claim supported
- version/license/pricing detail
- confidence
- unresolved ambiguity

### 6. Optional proof-of-concept

Only if necessary, keep it under:
`experiments/grokbot-zero-cost/`

A proof of concept MUST:
- be isolated
- not alter product runtime
- not deploy
- not make external side effects
- not require secrets
- default to local/mock/deterministic execution
- include instructions and verification output

Do not build a giant replacement application.

## Acceptance tests for your proposal

Your final proposal must make it possible for the integration owner to answer YES to all of these:

- Does Mimicus still have one control plane?
- Can the baseline run without paid SaaS?
- Can every external subsystem be removed?
- Are side effects still disabled by default?
- Is human approval explicit for future effects?
- Is memory authority still governed by Mimicus?
- Is evidence/provenance still canonical?
- Are redundant frameworks rejected unless a unique primitive is demonstrated?
- Is every recommended dependency license-safe?
- Is the Worker/Python boundary explicit?
- Are operational costs honestly separated from model inference costs?
- Can the proposal be integrated incrementally?
- Can every phase be rolled back?
- Is there enough evidence for another architect to audit the conclusions?

## Benchmark requirement

Do not recommend a new dependency solely from feature lists.

For any candidate that overlaps Mimicus, define a benchmark or falsification condition.

Examples:
- DeepEval: what evaluation does it add that internal benchmark cannot?
- Langfuse: what observability query/dashboard is currently missing?
- Graphiti: what temporal retrieval benchmark must it beat?
- Drex: what routing/selection task and calibration metric must improve?
- Browser Use: what browser task is materially easier/safer than Playwright?
- E2B: what isolation property is unavailable with local/Docker?

If no measurable win exists, recommend rejection/defer.

## Git discipline

Before work:
- confirm you are on `grokbot/mimicus-zero-cost-architecture`
- record starting SHA
- inspect latest remote refs read-only
- do not rebase onto concurrent branches without explicit instruction

During work:
- commit only your owned paths
- small coherent commits
- descriptive commit messages
- never force-push
- never rewrite shared history

At completion:
- push your branch
- report exact final SHA
- report changed paths
- report validation commands/results
- report external sources checked
- report unresolved risks
- DO NOT merge

## Return packet to Simón / integration owner

Return exactly:

1. branch
2. starting SHA
3. final SHA
4. commits
5. changed paths
6. architecture summary
7. $0 baseline summary
8. components recommended
9. components rejected/deferred
10. benchmarks/falsifiers required before adoption
11. verification performed
12. known limitations
13. merge/integration risks
14. explicit statement: "No shared branch merged or deployed."

## Decision posture

Be aggressive about useful capability, conservative about complexity.

The goal is NOT to maximize frameworks.
The goal is to maximize Mimicus capability per unit of:
- cost
- complexity
- authority risk
- maintenance burden
- operational dependency

Prefer small, replaceable adapters over platforms.

Treat all prior recommendations as hypotheses.

VERIFY > ASSUME.
