# Kimi K3 seed lineage

ORDER-002 treats the audited Kimi K3 archive as behavioral reference and seed lineage, not as executable production code.

## Audited artifact identities

| Artifact | SHA-256 |
|---|---|
| ZIP | `f170207468c60b25b0d9ec50ddfcf27366609d5e37773138ca76eb9124eb1478` |
| Python | `81b2fd83a313d9910f450ac54a4a1e48cd783dc1cde6bfc1d5bcfd37e6c38f2f` |
| SQL | `d596a293e8b3c3543e1ceaae1468c8a937f43428de5ddc60120cb77a39e204a4` |

| K3 contract | Legacy script SHA-256 | Safe MiMicus successor |
|---|---|---|
| `c1_tam_numerical_invariant` | `29625d238477193e2f4f1d636c66d38ce8e68dd776ad35c55c8dfd3a89f42b37` | F1 `numeric_invariant` |
| `c2_source_freshness` | `7649c98ea2c00f7623ed28b550539e971cee7ff63a43d5d6a8e028b7cdf3cd4b` | F2 `freshness` |
| `c3_source_independence` | `7e3dede7c5db53fe332b8a475e8c38010dd2c35bae43821db2f0ce4911fe521d` | F3 `source_independence` |
| `c4_citation_numeric_entailment` | `ff966c84029e43b8b71f5af3a39eb8fef875b79709aa7017458fc15bb8d0f501` | F4 `citation_entailment` |
| `c5_absence_counterexample_registry` | `8bc04b55871b7f5ed4f1aa87c47d9d40e7e40e15080c871330bc0c09affacc15` | F5 `counterexample_search` |

## Security boundary and intentional semantic changes

The legacy artifact persisted raw executable script text and executed it. MiMicus does neither. Runtime mutation yields only a validated `FalsifierSpec`; primitive dispatch is a closed source-controlled registry. No raw K3 script, SQL payload, or uploaded cache artifact is vendored.

Compatibility is behavioral, not hash emulation. `src/mimicus/falsifiers/k3_compat.py` preserves the K3 identities as metadata and exercises compatibility vectors, including the canonical approximately 12× TAM period mismatch. Missing/skipped evidence intentionally maps to `INCONCLUSIVE`, never `PASS`. Freshness validates malformed/future timestamps; source independence prioritizes provenance clusters; citation entailment binds the material figure to an evidence span; counterexample search pins the registry snapshot.

No source lines from the K3 Python or SQL artifact were copied. Implementation is clean-room from ORDER-002's audited behavior/specification.
