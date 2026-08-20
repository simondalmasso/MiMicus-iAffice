# ORDER-008 AUD Findings Closure

The evidence below is produced by executable probes. JSON `pass=true` values are emitted only after the referenced command exits with code 0; MCP evidence is emitted only after real server restarts, authenticated verification, supersession/revocation, and post-restart exclusion assertions complete.

- F038 — `CLAIM_BOUND_FALSIFIERS.json`
- F039 — `HIERARCHICAL_COMPOSITE_SYNTHESIS.json`
- F040 — `RECEIPT_CASCADE_REVOCATION.json`
- F041 — `EVIDENCE_PROJECTION_INTEGRITY.json`
- F042 — `VERIFIED_REMOVAL_SCOPE.json`
- F043 — `CORE_MEMORY_LEARN_PROGRESS.json`
- F044 — `SEMANTIC_REPLAY.json`
- Historical production regression F001-F037 — `RUNTIME_REGRESSION_F001_F037.txt`
- Three historical fixture compatibility regressions plus F038-F044 — `TEST_RESULTS.txt`
- Real MCP runtime / authenticated verification / restart / memory reuse / supersession / revocation / second restart / revoked-memory exclusion — `MCP_E2E.json`

The manifest covers every evidence file in this directory except `MANIFEST.sha256` itself. CI validates both the executable probes and the committed manifest.
