# ORDER-004 findings closure

| Finding | Closure | Evidence |
|---|---|---|
| F009 specialist-safe auditions | capability/test-family-scoped persistent calibration and bankruptcy; NOT_APPLICABLE is neutral; restart/recovery verified | `SPECIALIST_AUDITIONS.json` |
| F010 runtime-truth identity/correlation | exact fingerprint binds runtime provider/model/version plus phenotype/prompt/tools/policy/adapter; same runtime model is correlation-penalized | `RUNTIME_IDENTITY_CORRELATION.json` |
| F011 verified memory reaches online model | bounded eligible verified memory is serialized into sealed OpenAI structured input; quarantined memory excluded; usage counts consumed items | `OPENAI_MEMORY_INJECTION_MOCK.json` |
| F012 unified budget | one async-lock ledger reserves/reconciles agents, challenges and falsifiers; unknown/overrun fail closed; cancellation releases; zero budget blocks paid calls | `BUDGET_LEDGER.json` |
| F013 evidence persistence | run-scoped immutable evidence rows, canonical snapshot provenance, claim refs resolve after restart and replay | `EVIDENCE_PERSISTENCE.json` |
| F014 falsifier proximity | deterministic signatures and redundancy penalty suppress near duplicates while retaining complementary tests | `FALSIFIER_PROXIMITY.json` |
| F015 distinct morphologies | solo, paired verify, parallel fanout, sparse graph and hierarchical nested fanout/fanin compile to distinct structural signatures | `MORPHOLOGY_CLASSES.json`, `BENCHMARK_MORPHOLOGY_DISTRIBUTION.json` |
| F016 structured cancellation | task-group fatal fault cancels and awaits sibling; no delayed side effect survives | `STRUCTURED_CANCELLATION.json` |
| F017 neutral benchmark | 200 episodes/architecture on identical neutral public structured facts; common grader; anti-rigging and leakage rename probes; actual morphology/agent/challenge distributions | `BENCHMARK.json`, `BENCHMARK_RAW.jsonl`, `BENCHMARK_ANTI_RIGGING.json`, `BENCHMARK_LEAKAGE.json`, `BENCHMARK_MORPHOLOGY_DISTRIBUTION.json` |

F001..F008 regression is rerun through the ORDER-003 process E2E in `TEST_RESULTS.txt` and again by exact-head CI. No new PR and no merge.
