# MiMicus V0.1 architecture

## Boundary

MiMicus is the orchestration layer. External model SDKs are providers, not the source of authority for routing, promotion, memory, budget enforcement, hashing, or mutation.

The deterministic state flow is:

`INIT → PROFILE_TASK → LOAD_VERIFIED_MEMORY → AUDITION_CANDIDATES → SELECT_COALITION → SEALED_FIRST_PASS → BUILD_CLAIM_GRAPH → SCORE_FALSIFIER_MARKET → EXECUTE_FALSIFIERS → SPARSE_CHALLENGE → SYNTHESIZE_OR_REFUSE → ATTRIBUTE_CONTRIBUTIONS → LEARN_VERIFIED_ONLY → COMMIT_LEDGER`.

Each stage emits a hash-chained event. Replanning is driven by the progress ledger when uncertainty does not fall for two steps; it is not implemented as unconstrained extra debate.

## Package boundaries

- `plugins`: local capability kernel, immutable manifests, dependency ordering, reversible mount/unmount, explicit hash-checked out-of-tree path verification.
- `events`: typed in-process event bus plus canonical hash-chain ledger.
- `storage`: SQLAlchemy portable schema, SQLite repository, Alembic migrations, PostgreSQL DDL compatibility check.
- `providers`: scripted deterministic provider and OpenAI Agents SDK adapter.
- `agents`: fingerprints, task phenotypes, hidden micro-auditions, domain calibration, bankruptcy/recovery.
- `claims`: structured claim/evidence models and claim graph.
- `falsifiers`: validated DSL, five trusted primitives, immutable registry, utility-per-cost market, K3 compatibility vectors.
- `memory`: origin-bound authority plus WRITE/RETRIEVAL/PROMOTION/CROSS-AGENT gates.
- `coalition`: threat profile, dynamic coalition selection, correlated-error penalty, sparse communication topology.
- `germinal`: frozen fossil corpus, constrained parameter mutation, deterministic regression gate.
- `orchestration`: task/progress ledgers, engine, replay and removal attribution.
- `interfaces`: CLI and Streamable HTTP MCP server.

## Dynamic morphology

No fixed six-role debate exists. Candidate phenotypes are capabilities, not permanent seats. The selector greedily covers the threat profile with the smallest useful set while penalizing correlated provider/model/prompt/tool lineage. Simple numeric tasks select one numerical verifier; mixed source/freshness/numeric tasks require complementary members.

## Sealed independence

Every selected member receives a unique `sealed_context_id`; the engine records the first-pass claim before any sparse communication edge can open. Communications are value-ranked and only open under residual disagreement, bounded by `k` peers and three rounds.

## Deterministic authority

LLMs may propose claims. They cannot directly promote a memory item, mutate executable source, change a ledger hash, bypass a budget, or mark a falsifier as verified. Those transitions live in deterministic application code and are covered by security tests.
