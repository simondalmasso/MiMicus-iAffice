# Threat model

## Protected properties

MiMicus protects the integrity of verified claims, memory authority, calibration state, falsifier lineage, mutation promotion, budgets, effect authorization and replay evidence. It assumes source-controlled trusted primitives and the local process can be audited; it does not claim to protect a fully compromised host.

## Primary threats and controls

- **Dynamic-code injection**: Falsifier specs are declarative, extra fields are rejected, source-like parameter keys are rejected, mutation revalidates, and CI AST-scans production source for dynamic execution calls.
- **Memory poisoning/laundering**: origin authority is monotone non-increasing through derivation; promotion requires deterministic evidence or independent verified clusters. Retrieval similarity alone cannot grant authority.
- **Reputation laundering**: calibration is domain-scoped and direct-evidence gated.
- **Sybil/correlated clones**: lineage correlation reduces marginal coalition value.
- **Bankrupt-agent re-entry**: fresh recovery audition required.
- **Evasion farming**: repeated reports have no mutation authority without independently pinned confirmed ground truth.
- **Poisoned mutation**: declarative mutation only, frozen fossils, deterministic precision/recall/critical-regression promotion gate, immutable parent.
- **Ledger tamper**: each event is SHA-256 chained over canonical payload and prior hash; replay checks linkage, event hash and expected head.
- **Causal-result tamper**: causal replay recomputes the semantic Morphology-DAG contract and requires its semantic hash to match the chain-protected `causal_execution_recorded` ledger anchor. Mutable result JSON cannot self-authorize by re-hashing itself.
- **Effect substitution**: approval is bound to the exact canonical envelope hash. Payload, destination, resource, operation, scope or adapter changes invalidate the approval before dispatch.
- **Approval replay/race**: approvals are durable, time-bounded and atomically one-use. Concurrent consumers cannot both dispatch the same approved envelope.
- **Uncertain remote effect outcome**: an adapter exception after invocation produces `UNKNOWN`, keeps the approval consumed and forbids blind redispatch.
- **Credential capture in effect payloads**: raw credential-shaped fields are rejected before envelope approval/hashing.
- **Plugin replacement**: explicit path allow-list and exact source hash.
- **Provider stall**: OpenAI provider wraps a bounded async timeout; deterministic offline runs have no external model dependency.
- **Budget exhaustion**: market selection refuses tests outside budget; absence of decisive evidence yields `INCONCLUSIVE` rather than support.
- **Scheduler dependency violation**: the completion-driven executor admits a node only after all prerequisites are present in successful outputs; fatal failure cancels and awaits in-flight siblings.
- **Replay mismatch**: expected snapshot/head, semantic re-execution or causal-ledger-anchor mismatch fails verification.
- **Commercial observer authority confusion**: the observer is a read model only. It de-duplicates source changes and delegates decisions to `MiMicusEngine.triage_prospects`; it does not duplicate LAYA policy.
- **Observer network exposure**: the local observer HTTP server is loopback-only and read-only; mutation methods are rejected.

## Effect boundary

V0.2.2 contains an effect authorization and dispatch seam, but no autonomous real-world adapter is enabled by default. A real adapter must preserve the existing exact-envelope, one-use approval contract. Future browser/computer adapters also require explicit action admission and network-egress policy before they can be considered production-safe; those capabilities are not implied by the current effect seam.

## MCP exposure

The MCP server exposes only two narrow tools. `get_mimicus_run` is read-only/idempotent. `run_mimicus` can persist a run and, when `learn=true`, evidence-gated memory changes, so it is not annotated read-only or idempotent. The offline profile does not require an external model network call.
