# ORDER-006 audit findings closure

| Finding | Runtime closure | Executable evidence |
|---|---|---|
| F023 real hidden micro-auditions | typed provider audition path; Scripted executes hidden canaries; deterministic scorer; unsupported providers neutral; paid auditions use the unified budget ledger | `REAL_MICRO_AUDITIONS.json` |
| F024 verified adjudication | immutable hash-bound receipts, accepted authority classes, origin dedup, claim/run binding, exact contributor capability attribution, CLI/MCP submission | `VERIFICATION_RECEIPTS.json`, `MCP_E2E.json` |
| F025 runtime germinal loop | verified receipt contradicting persisted falsifier execution creates safe declarative mutation, fossil adjudication, persisted promotion/rejection and restart reuse | `RUNTIME_GERMINAL_LOOP.json`, `MCP_E2E.json` |
| F026 claim-aware falsifier market | market runs after sealed first-pass claims and records target claim hashes plus selection reason | `CLAIM_AWARE_FALSIFIER_MARKET.json` |
| F027 real synthesis | typed `SwarmDecision` returns candidate content separately from epistemic status and changes under linked falsifier evidence | `SWARM_DECISION_SYNTHESIS.json` |
| F028 genuine hierarchy | deterministic typed subtasks with distinct objectives/hashes are assigned to workers and nested fan-in is executed | `HIERARCHICAL_SUBTASKS.json` |
| F029 cofailure and marginal value | verified receipts persist pair cofailure and marginal signals; restart changes future coalition toward independent alternative | `COFAILURE_ATTRIBUTION.json` |
| F030 all five morphologies | all five runtime semantics are reachable; 200-episode architecture E benchmark exercises all five without force flags | `MORPHOLOGY_ALL_FIVE.json`, `BENCHMARK_MORPHOLOGY_DISTRIBUTION.json`, `BENCHMARK.json` |
| F031 structural threat profiling | evidence schema, prior verified failures, available capability/budget/concurrency and weak lexical signals are provenance-recorded; cosmetic wording invariance holds | `THREAT_PROFILE_STRUCTURAL.json` |

F001..F022 historical gates, security, ledger, coverage, migration and package evidence are rerun in `TEST_RESULTS.txt`, `LEDGER_VERIFY.json` and `PACKAGE_MIGRATION_DOCTOR.txt`.
