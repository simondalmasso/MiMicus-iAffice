# Falsifier DSL and K3 lineage

## Safe DSL

`FalsifierSpec` is immutable Pydantic data with: id, version, domain, trigger, trusted primitive, parameters, oracle kind, expected information gain, cost, latency, provenance, validity window and parent hash. Extra fields are rejected. Parameter keys representing executable source (`script`, `source`, `python`, `javascript`, `sql`, `code`) are rejected.

Runtime mutation reconstructs and revalidates the complete model. It does not use unchecked `model_copy(update=...)` for mutated parameters. No database or LLM text is passed to `exec`, `eval`, `compile`, a shell, or another dynamic source evaluator.

## V0.1 primitives

- F1 `numeric_invariant`: unit/period normalization and relative-tolerance arithmetic.
- F2 `freshness`: pinned evidence date relative to a requested `as_of` snapshot.
- F3 `source_independence`: provenance cluster count is primary; text similarity is only supplemental.
- F4 `citation_entailment`: a material claim figure must bind to a pinned evidence span that actually supports it.
- F5 `counterexample_search`: universal-negative claims query a pinned deterministic registry snapshot.

Every primitive returns exactly `PASS`, `FAIL`, or `INCONCLUSIVE`. Missing inputs, parsing ambiguity, missing provenance, or an unpinned registry never become `PASS`.

## K3 behavioral lineage

ORDER-002 records the supplied K3 artifact hashes without importing or executing their raw source:

- ZIP: `f170207468c60b25b0d9ec50ddfcf27366609d5e37773138ca76eb9124eb1478`
- Python: `81b2fd83a313d9910f450ac54a4a1e48cd783dc1cde6bfc1d5bcfd37e6c38f2f`
- SQL: `d596a293e8b3c3543e1ceaae1468c8a937f43428de5ddc60120cb77a39e204a4`

Contract hashes:

- C1: `29625d238477193e2f4f1d636c66d38ce8e68dd776ad35c55c8dfd3a89f42b37`
- C2: `7649c98ea2c00f7623ed28b550539e971cee7ff63a43d5d6a8e028b7cdf3cd4b`
- C3: `7e3dede7c5db53fe332b8a475e8c38010dd2c35bae43821db2f0ce4911fe521d`
- C4: `ff966c84029e43b8b71f5af3a39eb8fef875b79709aa7017458fc15bb8d0f501`
- C5: `8bc04b55871b7f5ed4f1aa87c47d9d40e7e40e15080c871330bc0c09affacc15`

The compatibility suite explicitly includes the canonical approximately-12× TAM mismatch and missing/skip vectors that must resolve to `INCONCLUSIVE`, not pass.

## Falsifier market

Candidate utility is proportional to expected information gain × applicability × evidence quality and inversely proportional to monetary cost + latency cost + risk cost. Selection is subject to task budget, maximum test count, and an information floor.
