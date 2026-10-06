# MiMicus V0.2.2 architecture

MiMicus V0.2.2 is a persistent agentic immune swarm runtime. The normal engine is assembled through the plugin kernel into typed functional services for storage, model/provider access, agent factories, falsifiers, memory, coalition selection, sparse communication, sandbox policy, telemetry, commercial lead decisions and effect dispatch.

## Runtime control plane

There is one orchestration control plane: `MiMicusEngine`. External swarm frameworks are not nested inside it. `build_runtime_services()` resolves functional built-ins through `PluginKernel`; the engine consumes the resulting `RuntimeServices`. Provider replacement is an adapter concern and does not require changing orchestration logic.

The canonical execution plan is a hashable Morphology DAG. Supported node kinds are `PROFILE`, `MEMORY_RETRIEVE`, `AUDITION`, `DECOMPOSE`, `AGENT_TASK`, `FALSIFIER`, `CHALLENGE`, `JOIN`, `SYNTHESIS`, `LEARN` and `GERMINAL`. The compiler chooses the smallest sufficient plan from task threat profile, selected agents, available falsifiers, complexity, budget and concurrency constraints. It can emit `solo`, `parallel_fanout`, `paired_verify`, `sparse_graph` and `hierarchical_fanout_fanin` plans with distinct executable topology. Paired and sparse plans contain different challenge semantics; hierarchical plans contain decomposition plus nested fan-out/fan-in.

Dependencies are executable. `DagExecutor` admits only ready nodes, fills capacity deterministically by node ID, then waits for the first completion rather than a whole ready batch. A newly eligible descendant can therefore start while an unrelated slow sibling remains in flight. Fatal node failure cancels all in-flight siblings and awaits cancellation before returning. Plan hashes, node input/output hashes, terminal statuses, scheduling evidence, critical-path measurements and peak concurrency are included in run provenance.

## Runtime-truth identity and calibration

An exact agent fingerprint binds the material execution identity: runtime provider ID, configured model ID and runtime-model version marker, phenotype and phenotype version, system-prompt hash, tool-manifest hash, policy hash and provider-adapter version. `ProviderCapabilities` is the runtime source for provider/model identity; phenotype labels do not manufacture provider diversity. Material identity changes produce a different exact fingerprint. Lineage is separate from exact identity so negative lineage evidence can cause probation without laundering a predecessor's positive trust.

Calibration and bankruptcy are scoped by exact fingerprint, domain, audited capability and test family. A canary outside an agent's relevant capability is `NOT_APPLICABLE` and does not count as a failure. Routing uses the capability-scoped state; the historical domain-level bankruptcy/probation projection is retained only for compatibility and inspection.

## Persistent immune state and online memory

SQLite and PostgreSQL-compatible storage includes runs/events plus authority-bearing calibration, bankruptcy/probation, exact fingerprints, lineages, coalition plans, communications, claims, evidence, falsifier versions/executions/performance, evasion events, fossils, mutation candidates, memory items/links/transitions, task ledgers, progress ledgers, effect approvals and effect intents.

A run retrieves persisted verified memory and promoted falsifiers before execution. Memory still passes MiMicus RETRIEVAL and CROSS-AGENT gates before injection. The OpenAI adapter serializes only eligible verified institutional memory into a bounded structured input; quarantined/rejected memory does not consume eligible-memory slots. The sealed first pass explicitly excludes peer outputs. Provider usage records the number of verified-memory items actually consumed.

Memory authority remains policy-driven rather than similarity-driven. Retrieval can surface candidates, but candidate retrieval alone does not promote memory into a trusted state.

## Budget and falsifier market

One concurrency-safe `BudgetLedger` owns the hard monetary cap for agent generation, challenges and falsifiers. Paid work reserves capacity before launch and reconciles against known actual cost. Unknown monetary cost retains its reservation and is reported as `UNKNOWN`; a provider overrun fail-closes later paid work. Cancellation releases unreconciled reservations. Falsifier-market selection receives only remaining monetary capacity.

Falsifier selection uses deterministic signatures over primitive, trigger tokens, evidence targets, oracle kind and normalized parameter bands. Near-duplicate tests compete as substitutes with an explicit redundancy penalty; complementary tests remain eligible when they add information.

## Evidence persistence

Runtime evidence is normalized into immutable structured rows with provenance, observed time, extraction method, independence cluster and snapshot hash. Claims reference only evidence rows MiMicus persists. Evidence references are run-scoped to avoid cross-run primary-key collisions while retaining a canonical content hash. `get_run` and replay inspection enumerate persisted evidence and permit reference resolution after process restart.

## Commercial decision boundary

The commercial slice remains subordinate to LAYA. `MiMicusEngine.triage_prospects(...)` normalizes setter-shaped prospect data and delegates to `DeterministicLeadDecisionService`. It is deterministic for identical normalized inputs, policy and explicit `as_of`, and performs no model call, network call, setter-ledger mutation or external outreach.

The optional local commercial observer reads file or HTTPS prospect sources, de-duplicates by content hash and publishes a read-only loopback activity model. It does not become a second decision engine; authoritative decisions still come from the same `triage_prospects` path.

## Effect authorization boundary

External effects are deny-by-default. Before future tools may bypass the effect boundary, `ActionAdmissionPolicy` must explicitly classify the exact adapter + operation pair as `READ_ONLY`; `MUTATING` and unclassified `UNKNOWN` actions cannot bypass that gate. `EffectActionEnvelope` binds adapter, operation, destination, resource, payload and scope into a canonical hash. A durable `EffectApprovalReceipt` authorizes exactly that hash for a bounded time window and can be consumed only once.

`EffectDispatcher` verifies adapter identity before consuming the approval. Successful dispatch persists an outcome hash. If the adapter raises after invocation, the intent becomes `UNKNOWN`; the approval remains consumed and Mimicus does not blindly retry because the remote side effect may already have happened. V0.2.2 ships the authorization/dispatch seam but no autonomous real-world adapter.

## Sparse communication

Communication edges are not descriptive metadata. A selected edge creates a structured `ChallengeRequest`, reserves budget, invokes the provider challenge adapter, receives a `ChallengeResponse`, revises the target claim and records round, reason, provider call ID and input/output hashes. Raw hidden chain-of-thought is never exchanged.

## Germinal learning

Only a confirmed evasion with pinned ground truth can enter the germinal path. Declarative mutation candidates remain derived from trusted primitives, run frozen fossils and receive a deterministic PROMOTE/REJECT/QUARANTINE decision. Promotion and provenance are persisted transactionally; the parent remains immutable and replayable. Later processes can retrieve a promoted falsifier.

## Neutral execution-derived benchmark

ORDER-004 uses the same ordered public structured-evidence stream for architectures A-E and a single architecture-blind post-run grader. Ground truth is separate from provider inputs. Task wording and fixture IDs do not encode the answer; a leakage probe renames task text while holding public facts constant and requires an unchanged verdict. Reports include actual MiMicus morphology, agent-count and challenge-edge distributions instead of assuming those execution paths occurred.

## Determinism and replay

Semantic identities, plan hashes, claim/falsifier/evidence hashes and the event chain are deterministic inputs to replay verification. Monotonic durations, scheduler-turn timing and wall timing are preserved as incidental evidence but are not treated as semantic truth.

V0.2.2 adds a causal execution contract for the Morphology DAG. The semantic projection binds node IDs, kinds, prerequisites, terminal states and output hashes, while excluding incidental scheduler timing. Its semantic hash is recorded in the append-only event ledger and included in the semantic replay snapshot. Replay therefore verifies both the recomputed causal contract and its chain-protected ledger anchor; re-hashing a tampered mutable result snapshot cannot manufacture a successful replay.

ORDER-002 and ORDER-003 evidence remain historical. Later ORDER evidence and the current exact-head CI gates extend those proofs without replacing the single MiMicus control plane. No arbitrary generated-code execution path is introduced by V0.2.2.
