# MiMicus V0.2 architecture

MiMicus V0.2 is a persistent agentic immune swarm runtime. The normal engine is assembled through the plugin kernel into typed functional services for storage, model/provider access, agent factories, falsifiers, memory, coalition selection, sparse communication, sandbox policy and telemetry.

## Runtime control plane

There is one orchestration control plane: `MiMicusEngine`. External swarm frameworks are not nested inside it. `build_runtime_services()` resolves functional built-ins through `PluginKernel`; the engine consumes the resulting `RuntimeServices`. Provider replacement is an adapter concern and does not require changing orchestration logic.

The canonical execution plan is a hashable Morphology DAG. Supported node kinds are `PROFILE`, `MEMORY_RETRIEVE`, `AUDITION`, `AGENT_TASK`, `FALSIFIER`, `CHALLENGE`, `JOIN`, `SYNTHESIS`, `LEARN` and `GERMINAL`. The compiler chooses the smallest sufficient plan from task threat profile, selected agents, available falsifiers, complexity, budget and concurrency constraints. It can emit `solo`, `parallel_fanout`, `paired_verify`, `sparse_graph` and justified `hierarchical_fanout_fanin` plans.

Dependencies are executable: `DagExecutor` schedules only ready nodes and runs independent ready work concurrently up to `max_concurrency`. Plan hashes, node input/output hashes, scheduling evidence and critical-path measurements are included in run provenance.

## Persistent immune state

SQLite and PostgreSQL-compatible storage includes runs/events plus authority-bearing calibration, bankruptcy/probation, exact fingerprints, lineages, coalition plans, communications, claims, evidence, falsifier versions/executions/performance, evasion events, fossils, mutation candidates, memory items/links/transitions, task ledgers and progress ledgers.

A run retrieves persisted verified memory and promoted falsifiers before execution. Memory still passes MiMicus RETRIEVAL and CROSS-AGENT gates before injection. Persisted state is policy input, not automatic authority.

## Sparse communication

Communication edges are not descriptive metadata. A selected edge creates a structured `ChallengeRequest`, invokes the provider challenge adapter, receives a `ChallengeResponse`, revises the target claim and records round, reason, provider call ID and input/output hashes. Raw hidden chain-of-thought is never exchanged.

## Germinal learning

Only a confirmed evasion with pinned ground truth can enter the germinal path. Declarative mutation candidates remain derived from trusted primitives, run frozen fossils and receive a deterministic PROMOTE/REJECT/QUARANTINE decision. Promotion and provenance are persisted transactionally; the parent remains immutable and replayable. Later processes can retrieve a promoted falsifier.

## Determinism and replay

Semantic identities, plan hashes, claim/falsifier hashes and the event chain are deterministic inputs to replay verification. Monotonic duration and wall timing are preserved as evidence but are not treated as semantic truth. No arbitrary generated code execution path is introduced by V0.2.

ORDER-002 evidence remains historical. ORDER-003 supersedes its architecture-scripted benchmark methodology with execution-derived runners and a common post-run grader.
