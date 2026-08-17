# Threat model

## Protected properties

MiMicus protects the integrity of verified claims, memory authority, calibration state, falsifier lineage, mutation promotion, budgets and the replay ledger. It assumes source-controlled trusted primitives and the local process can be audited; it does not claim to protect a fully compromised host.

## Primary threats and controls

- **Dynamic-code injection**: Falsifier specs are declarative, extra fields are rejected, source-like parameter keys are rejected, mutation revalidates, and CI AST-scans production source for dynamic execution calls.
- **Memory poisoning/laundering**: origin authority is monotone non-increasing through derivation; promotion requires deterministic evidence or independent verified clusters.
- **Reputation laundering**: calibration is domain-scoped and direct-evidence gated.
- **Sybil/correlated clones**: lineage correlation reduces marginal coalition value.
- **Bankrupt-agent re-entry**: fresh recovery audition required.
- **Evasion farming**: repeated reports have no mutation authority without independently pinned confirmed ground truth.
- **Poisoned mutation**: declarative mutation only, frozen fossils, deterministic precision/recall/critical-regression promotion gate, immutable parent.
- **Ledger tamper**: each event is SHA-256 chained over canonical payload and prior hash; replay checks linkage, event hash and expected head.
- **Plugin replacement**: explicit path allow-list and exact source hash.
- **Provider stall**: OpenAI provider wraps a bounded async timeout; deterministic offline runs have no external model dependency.
- **Budget exhaustion**: market selection refuses tests outside budget; absence of decisive evidence yields `INCONCLUSIVE` rather than support.
- **Replay mismatch**: expected snapshot/head mismatch fails verification.

## MCP exposure

The MCP server exposes only two narrow tools. `get_mimicus_run` is read-only/idempotent. `run_mimicus` can persist a run and, when `learn=true`, evidence-gated memory changes, so it is not annotated read-only or idempotent. The offline profile does not require an external model network call.
