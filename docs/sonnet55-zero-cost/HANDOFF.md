# SONNET 5.5 HIGH HANDOFF — Mimicus $0 Architecture Challenge

## ROLE

You are an independent senior architecture worker for **Mimicus iAffice**.

Your task is to produce a second, independent architecture proposal for the strongest practical **mandatory-cost-$0 Mimicus**, preserving the existing Mimicus control plane and avoiding redundant frameworks.

You are NOT the final integration owner.
Your proposal will later be audited, corrected, refined, benchmarked and selectively integrated by the Mimicus AUD/ARQ worker.

## REPOSITORY + YOUR BRANCH

Repository:
https://github.com/simondalmasso/the-iAffice

YOUR ONLY WRITE BRANCH:
`sonnet55/mimicus-zero-cost-architecture`

Branch point:
`mimicus-v2-monochrome@f9d185203e5ab9362a56dda2dcd7fd38e39db22f`

Push ALL your work ONLY to your branch.

DO NOT push to:
- `main`
- `mimicus-v2-monochrome`
- any AUD/ARQ branch
- any Facebook Setter branch
- any Reddit Setter branch
- `grokbot/mimicus-zero-cost-architecture`

DO NOT MERGE.
DO NOT DEPLOY.
DO NOT mark PR #9 ready.
DO NOT delete repos, history, evidence, archives or branches.
DO NOT force-push.

## CONCURRENT WORKERS — IMPORTANT

The project already has simultaneous workers:

1. Mimicus AUD/ARQ — final architecture/audit/integration owner.
2. Facebook Setter — separate workstream.
3. Reddit Setter — separate workstream.
4. Grokbot — independent $0 architecture proposal.
5. You / Sonnet 5.5 High — independent second architecture proposal.

Assume other branches will change while you work.

You must remain mergeable and isolated.

## INDEPENDENCE RULE

Do NOT anchor yourself on Grokbot's conclusions.

First:
- inspect the real Mimicus repository,
- inspect the absorbed MiMicus source,
- research current external candidates,
- freeze your own architecture.

Only AFTER your own proposal is complete may you optionally inspect:
`docs/grokbot-zero-cost/**`
or any Grokbot artifact for a comparison appendix.

If you compare later:
- state agreements,
- disagreements,
- which proposal is simpler,
- which has better $0 properties,
- which claims still need verification.

Do NOT copy Grokbot architecture blindly.

## YOUR WRITE OWNERSHIP

Prefer adding files ONLY under:

`docs/sonnet55-zero-cost/`

Optional proof-of-concepts, only if necessary:

`experiments/sonnet55-zero-cost/`

Do NOT modify shared product surfaces:

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

If you believe a shared file should eventually change, describe the exact proposed change in your integration plan. Do not make it yourself.

## CURRENT PRODUCT STATE

Product:
**Mimicus iAffice**

Active product branch:
`mimicus-v2-monochrome`

Known branch HEAD:
`f9d185203e5ab9362a56dda2dcd7fd38e39db22f`

PR:
https://github.com/simondalmasso/the-iAffice/pull/9

PR #9 is intentionally:
**DRAFT / NO MERGE**

Known deployment:
https://mimicus.simondalmasso44.workers.dev

Known Cloudflare Worker Version ID:
`8840605b-6249-498c-8c78-fbc434405dc9`

Known live state at branch point:
- root HTTP 200
- `/api/health` -> `ok=true`
- service = `mimicus`
- ui = `monochrome-v2`

V1 is:
**simulation-safe**

External side effects:
**OFF by default**

## VISUAL / PRODUCT IDENTITY

The product already has a canonical visual direction.

Preserve:
- black / grayscale monochrome
- LAYA central supervisor
- radial agent network
- extremely slow / smooth motion
- restrained autonomous-control-room feeling
- Activity Stream at bottom
- no flashy redesign
- no unrelated UI framework migration

Architecture comes first; do not redesign Mimicus.

## ABSORBED MIMICUS SOURCE

Original source repo:
https://github.com/simondalmasso/MiMicus-swarm

Canonical source branch:
`order-002-mimicus-v01`

Exact source HEAD:
`565407eb1296eae617f5b14b512d2e0cf08c6c02`

Absorbed under:
`archive/MiMicus-swarm-source/`

Previously verified:
- exact source commit exists in both repos
- source commit is in target ancestry
- subtree merge commit:
  `038ce795f16d193bb31a9308435724f6d73822eb`
- subtree split:
  `565407eb1296eae617f5b14b512d2e0cf08c6c02`
- source blobs = 311
- archive blobs = 311
- missing = 0
- extra = 0
- SHA/mode mismatch = 0

One thing remains unresolved:
a literal clean-shell fresh clone verification was not previously completed because the execution shell had DNS failure.

Therefore:
- do not claim fresh-clone verification unless YOU reproduce it
- do not recommend deleting the old source repo until that succeeds

VERIFY > ASSUME.

## EXISTING MIMICUS CORE — THESE ARE INVARIANTS

The absorbed Python source is NOT an empty prototype.

### ONE CONTROL PLANE

- LAYA is supervisor.
- `MiMicusEngine` is the orchestration authority.
- There must remain ONE orchestration control plane.
- Do not nest another swarm framework.
- Do not create a second supervisor/control plane.

### MORPHOLOGY ENGINE

Existing morphologies include:

- `solo`
- `paired_verify`
- `parallel_fanout`
- `sparse_graph`
- `hierarchical_fanout_fanin`

Canonical execution representation:
`Morphology DAG`

Execution:
`DagExecutor`

Existing concerns include:
- bounded concurrency
- cancellation
- plan hashes
- provenance
- replay
- deterministic fixtures
- exact agent fingerprints
- evidence
- falsification
- budget tracking

Do not replace these merely because another framework also has workflows/graphs.

### MEMORY AUTHORITY

Mimicus memory authority is governed by policy.

Authority is NOT vector similarity.

Memory lifecycle includes:
- candidate
- quarantined
- private_verified
- shared_verified
- rejected
- expired

Gates exist around:
- WRITE
- PROMOTION
- RETRIEVAL
- CROSS-AGENT use

External graph/vector/retrieval systems may retrieve candidates.
They MUST NOT decide memory authority.

### EXISTING EXTENSION SEAMS

The source already exposes services/adapters around:

- storage
- provider
- agent factory
- falsifiers
- memory
- coalition
- communication
- sandbox
- telemetry

Known implementations include:
- `LocalSandboxService`
- `LedgerTelemetryService`
- governed memory
- coalition services
- sparse communication

Prefer adding capability through these seams.

### EXISTING BENCHMARK / PROVENANCE

Mimicus already contains non-trivial:
- deterministic fixtures
- architecture comparisons
- replay verification
- provider-call metrics
- communication metrics
- falsifier metrics
- memory metrics
- germinal-work metrics
- critical path
- wall time
- parallel efficiency
- cost
- anti-rigging evidence

External evaluation systems must prove NET NEW VALUE.

## EXISTING PYTHON PROJECT

Current absorbed project:
`mimicus-swarm 0.2.2`

Python:
`>=3.12,<3.15`

Known dependencies include:
- `openai-agents==0.21.1`
- `pydantic==2.13.4`
- `SQLAlchemy==2.0.50`
- `alembic==1.18.4`
- `mcp==2.0.0`

Dev/test:
- pytest
- pytest-cov
- mypy
- ruff

Coverage gate:
90%

Important:
Mimicus ALREADY uses Pydantic and OpenAI Agents.
Do not introduce another framework to solve a problem already solved.

## CURRENT CLOUDFLARE PRODUCT

The deployed product is currently intentionally small.

Current active root approximately contains:
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
- Cloudflare Worker
- static assets
- `/api/health`
- `/api/runtime`
- UI otherwise
- minimal/no runtime dependencies
- effects OFF

Your architecture MUST clearly distinguish:

1. Cloudflare Worker cockpit / edge API
2. absorbed Python orchestration core
3. local runtime
4. optional execution backends
5. persistence
6. browser/sandbox
7. what actually stays $0

Do not hand-wave Worker <-> Python integration.

This is a major architecture question.

## DEFINITION OF "$0"

Target:
**maximum useful Mimicus capability with zero mandatory monetary cost.**

Design a baseline that can operate with no mandatory paid SaaS for:

- local development
- tests
- evaluations
- baseline orchestration
- baseline persistence
- telemetry
- sandboxing
- browser automation where practical

Rules:

- Prefer open-source/local.
- Prefer existing infrastructure.
- Free tiers may be OPTIONAL accelerators only.
- Core architecture cannot depend on a free trial.
- Core cannot stop because a SaaS quota expires.
- Every paid/freemium adapter needs a zero-cost fallback.
- Separate infrastructure cost from inference/API cost.
- Do NOT call paid LLM tokens "$0".
- Avoid unnecessary DBs, queues, control planes and SaaS.
- Avoid idle infrastructure.
- Avoid framework tourism.
- Explicit licenses matter.
- Do not copy code with unclear license.

## CANDIDATES TO INDEPENDENTLY VERIFY

Treat these as hypotheses, not prior decisions.

Evaluate current status, license, version, maintenance, self-hosting, free limits and real overlap.

### Open Dot / composio-community/open-dot

Potentially useful patterns:
- allow / ask / never effect rules
- human takeover
- browser/computer backend abstraction
- local/docker/cloud concepts
- integrations/triggers

Prior concern:
an explicit LICENSE was not observed in an earlier review.

Verify it yourself.
If unclear:
DO NOT COPY CODE.

### Nace / Drex

Potentially interesting:
constrained decisions over explicit options/probabilities.

Possible Mimicus role:
OPTIONAL `DecisionProvider`

Use cases:
- routing
- morphology selection
- coalition selection

Must not become LAYA authority.
Must prove measurable value.

Verify:
- current availability
- license
- API/self-hosting
- price
- zero-cost viability
- privacy
- maintenance

### Graphiti / Zep

Potential net-new area:
temporal / bi-temporal knowledge retrieval.

Possible role:
OPTIONAL subordinate retriever/index.

Never memory authority.

Adopt only if it wins a real temporal-retrieval benchmark.

### Langfuse

Potential value:
- traces
- observability
- eval dashboards
- possible OpenTelemetry integration

Possible role:
OPTIONAL telemetry/export sink.

Canonical Mimicus evidence must remain internal.

### DeepEval

Potential value:
- standardized agent/LLM evaluation
- component/trajectory evaluation
- pytest integration

Possible role:
DEV/EVAL ONLY.

Must add something Mimicus cannot already evaluate.

### Browser Use

Potential value:
browser automation/session primitives.

Constraint:
do NOT embed its autonomous agent loop as a second control plane.

Compare with direct Playwright.

Preferred mental model:
`BrowserActuator` under Mimicus DAG + approval/effect policy.

### E2B

Potential value:
isolated sandbox execution.

Possible role:
OPTIONAL `SandboxService` backend.

Baseline should remain local.
Docker may be optional.
E2B cannot be mandatory for "$0".

### General frameworks

Evaluate, but assume nothing:

- LangGraph
- CrewAI
- AutoGen
- PydanticAI
- Dify
- Mastra
- Agno / AgentOS
- Semantic Kernel / Microsoft Agent Framework
- n8n if relevant

For each:
ask whether it adds a separable primitive or merely duplicates:
- supervisor
- DAG
- workflow
- memory
- telemetry
- approvals
- tools
- agents
- state

If it is another control plane:
REJECT as core.

If one small primitive is genuinely useful:
describe how to absorb the pattern/adapter without importing a second orchestration authority.

## INSFORGE

Do NOT add InsForge by default.

Only recommend it if you prove:
1. Mimicus actually lacks the capability,
2. the need is concrete,
3. it is simpler than alternatives,
4. it preserves $0 baseline,
5. it does not duplicate storage/auth/runtime already available.

## YOUR MAIN QUESTION

Answer:

**What is the maximum useful Mimicus architecture we can build at mandatory monetary cost $0 while keeping LAYA / MiMicusEngine as the single orchestration authority and avoiding redundant frameworks?**

Use current sources, not stale model memory.

Prefer primary sources:
- official GitHub
- LICENSE
- official docs
- official pricing
- release notes
- self-host docs

## REQUIRED ANALYSIS

Evaluate at minimum:

1. control plane
2. Morphology DAG
3. scheduling/concurrency
4. provider/model routing
5. decision abstraction
6. memory
7. retrieval
8. temporal knowledge
9. provenance/evidence
10. telemetry
11. observability
12. evaluations
13. browser actuator
14. sandbox/code execution
15. human approval
16. effect policy
17. MCP/tool integrations
18. persistence
19. Cloudflare Worker boundary
20. Python core boundary
21. local development
22. replay/determinism
23. security
24. deployment topology
25. cost model
26. degradation modes
27. migration path

For each subsystem classify:

- KEEP AS-IS
- REFACTOR INTERNAL
- OPTIONAL ADAPTER
- EXPERIMENT ONLY
- REJECT / REDUNDANT
- DEFER

Do not use arbitrary scores.

## NON-NEGOTIABLE RULES

1. LAYA / MiMicusEngine remains the only orchestration authority.
2. No nested swarm framework.
3. No second control plane.
4. Memory policy stays canonical.
5. Evidence/provenance stays canonical.
6. External adapters gain no authority.
7. Effects OFF by default.
8. Future external effects require explicit human approval policy.
9. $0 baseline works with all SaaS disabled.
10. All optional pieces are removable.
11. No vendor lock-in.
12. No code copy from unclear licenses.
13. No production deploy.
14. No shared merge.
15. VERIFY > ASSUME.

## IMPORTANT LESSON FROM PRIOR GROKBOT ATTEMPT

A previous independent worker produced an architecture prototype that drifted into a new Next.js/PostgreSQL application instead of staying centered on the actual Cloudflare Worker + absorbed Python core.

Do NOT repeat that.

You may propose Next.js/PostgreSQL only if you can prove they are materially necessary and superior to the current stack.

Default burden of proof is:
**preserve existing runtime unless the replacement solves a measured problem.**

Also watch for fake determinism:
- `Math.random()`
- wall-clock timestamps
- regenerated plan hashes
- nondeterministic ordering

Do not call a system replayable/deterministic unless the evidence supports it.

Do not call `parallel_fanout` parallel unless actual concurrent scheduling exists.

## PREFERRED TARGET SHAPE TO CHALLENGE

Do not blindly accept this. Improve or reject pieces with evidence.

Possible baseline:

Cloudflare Worker:
- cockpit
- edge health/runtime API
- static UI

Python Mimicus core:
- authoritative `MiMicusEngine`
- Morphology DAG
- DagExecutor
- memory/falsification/provenance
- local execution

Persistence:
- SQLite baseline
- PostgreSQL only optional if proven necessary

Telemetry:
- canonical Mimicus ledger
- optional OpenTelemetry export
- optional Langfuse sink

Evaluation:
- existing benchmark first
- optional DeepEval adapter only if net-new

Sandbox:
- local allowlisted baseline
- optional Docker
- optional E2B

Browser:
- direct Playwright baseline
- Browser Use only if benchmark proves net value

Decision:
- Mimicus-native baseline
- optional Drex-like experimental `DecisionProvider`

Temporal retrieval:
- existing memory first
- optional Graphiti only if it wins benchmark
- never authority

General orchestration frameworks:
- no core adoption unless a uniquely separable primitive is demonstrated

No mandatory SaaS.

## REQUIRED DELIVERABLES

Create and push:

### 1.
`docs/sonnet55-zero-cost/ARCHITECTURE.md`

Include:
- executive architecture
- rationale
- component diagram
- control flow
- data flow
- authority/trust boundaries
- effect boundaries
- Worker/Python boundary
- $0 topology
- optional topology
- failure/degradation behavior
- security model
- migration phases
- rejected alternatives
- unresolved questions

Use Mermaid where useful.

### 2.
`docs/sonnet55-zero-cost/CAPABILITY-MATRIX.md`

For each candidate include:
- capability
- already in Mimicus?
- project
- net-new value
- overlap
- exact license
- local/self-host?
- mandatory cost
- optional cost
- infra requirements
- operational complexity
- security/effect implications
- recommendation
- source

### 3.
`docs/sonnet55-zero-cost/COST-MODEL.md`

Separate:
- license
- hosting
- DB
- storage
- bandwidth
- CI
- observability
- browser
- sandbox
- inference
- embeddings
- reranking
- graph infra

For every "$0" statement, state the conditions.

### 4.
`docs/sonnet55-zero-cost/INTEGRATION-PLAN.md`

For every phase:
- objective
- paths
- interfaces
- dependencies
- feature flags/defaults
- authority effect
- side-effect effect
- acceptance test
- benchmark/falsifier
- rollback
- cost impact
- complexity impact

### 5.
`docs/sonnet55-zero-cost/EVIDENCE.md`

For every important external claim record:
- URL
- project
- source type
- checked date
- supported claim
- version
- exact license
- price/free-tier detail
- self-host detail
- confidence
- unresolved ambiguity

### 6. Optional independent comparison

Only AFTER your architecture is frozen:

`docs/sonnet55-zero-cost/COMPARISON-WITH-GROKBOT.md`

Compare architectures without changing yours merely to converge.

## OPTIONAL PROOF OF CONCEPT

Only when required to falsify an architectural claim.

Keep under:
`experiments/sonnet55-zero-cost/`

Rules:
- isolated
- no deployment
- no secrets
- no external side effects
- deterministic/local/mock default
- reproduction instructions
- verification output
- no replacement app

## BENCHMARK / FALSIFICATION RULE

Never adopt a dependency based only on features.

Examples:

Graphiti:
must beat a defined temporal query baseline.

Drex:
must improve routing/calibration vs Mimicus baseline.

Langfuse:
must answer operational/debug queries the local ledger cannot conveniently answer.

DeepEval:
must express/measure a useful eval absent from Mimicus benchmark.

Browser Use:
must outperform direct Playwright on a defined task dimension.

E2B:
must provide isolation that local/Docker cannot reasonably provide.

General frameworks:
must expose one separable primitive with measurable benefit.

No measurable benefit:
REJECT or DEFER.

## GIT DISCIPLINE

Before work:
- confirm branch:
  `sonnet55/mimicus-zero-cost-architecture`
- record starting SHA
- fetch refs read-only
- do not rebase concurrent work

During:
- only your owned paths
- small coherent commits
- no force-push
- no shared branch mutation

At completion:
- PUSH YOUR BRANCH
- verify remote HEAD actually advanced
- report exact final SHA
- report commit list
- report changed paths
- report validation
- DO NOT MERGE
- DO NOT DEPLOY

A ZIP or local workspace alone is NOT considered delivery if remote branch was supposed to receive the work.

## RETURN PACKET

Return exactly:

1. branch
2. starting SHA
3. final remote SHA
4. commits
5. changed paths
6. architecture summary
7. exact $0 baseline
8. recommended components
9. rejected components
10. deferred components
11. experimental components
12. benchmarks/falsifiers
13. verification performed
14. external sources checked
15. license findings
16. known limitations
17. integration risks
18. assumptions still unverified
19. exact statement:
   **"No shared branch merged or deployed."**

## DECISION POSTURE

Be aggressive about REAL capability.
Be conservative about complexity.

Optimize for:
- capability
- $0 operation
- removability
- auditability
- determinism
- security
- low maintenance
- low authority risk

Do NOT optimize for:
- framework count
- novelty
- platform adoption

Prefer:
small Mimicus-native adapters
over
new control planes.

Prefer:
measured capability
over
marketing claims.

VERIFY > ASSUME.
