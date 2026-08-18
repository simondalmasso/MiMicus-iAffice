# ORDER-007 audit findings closure

| Finding | Runtime closure | Executable evidence |
|---|---|---|
| F032 authenticated verification authority | immutable server-side verifier policy, secret hash authentication, run-bound proof hashes, same-origin dedup, active-receipt supersession rebuild | `VERIFIER_AUTHORITY_BINDING.json`, `MCP_E2E.json` |
| F033 immutable claim lineage | semantic/evidence identity hash is stable; challenge revision hash is separate; falsifier, communication, synthesis, receipt and germinal target the stable identity | `CLAIM_IDENTITY_LINEAGE.json` |
| F034 claim-born falsifier market + F014 novelty | full safe registry is scored after sealed claims; promoted lineage ancestors are suppressed; actual claim market applies proximity/novelty | `CLAIM_MARKET_NOVELTY.json` |
| F035 complete isolated hierarchy | every required subtask is assigned by capability or marked unresolved; evidence is scoped; subgroup joins are isolated; incomplete hierarchy fails closed | `HIERARCHY_COMPLETE_EXECUTION.json` |
| F036 removal attribution | episode-bound leave-one-out counterfactual deltas are persisted separately from success/failure/cost/decisive-test features | `REMOVAL_ATTRIBUTION.json` |
| F037 runtime core lock | normal Python/CLI/MCP runtime cannot select fixture/legacy semantics; fixture lane remains explicit compatibility only | `RUNTIME_CORE_LOCK.json`, `MCP_E2E.json` |

F001..F031 are rerun in `REGRESSION_F001_F031.txt` and the full quality/security suite is recorded in `TEST_RESULTS.txt`.
