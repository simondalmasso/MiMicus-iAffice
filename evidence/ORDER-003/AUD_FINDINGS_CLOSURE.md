# ORDER-003 AUD findings closure

| Finding | Integrated implementation | Direct tests | Exact evidence |
|---|---|---|---|
| F001 persistent immune state | `src/mimicus/storage/models.py`, `storage/repository.py`, `plugins/services.py`, `orchestration/engine.py`, Alembic `0002_order003_runtime.py` | `test_repository_persists_calibration_memory_falsifier_and_identity`, restart integration tests | `PERSISTENCE_RESTART.json`, `MIGRATION_VERIFY.txt` |
| F002 memory retrieval/reuse | `memory/gates.py`, `memory/retrieval.py`, repository memory transitions, engine run-start retrieval and CROSS-AGENT gating | `test_engine_restart_memory_reuse_and_falsifier_germinal_reuse`, process memory seed/reuse | `MEMORY_REUSE.json`, `PERSISTENCE_RESTART.json` |
| F003 bankruptcy enforcement | `agents/calibration.py`, `agents/bankruptcy.py`, `agents/identity.py`, repository lineage state, engine pre-selection exclusions/recovery | `test_bankruptcy_enforcement_whitewash_probation_and_recovery` | `BANKRUPTCY_LINEAGE.json` |
| F004 real sparse communication | `orchestration/communication.py`, provider `ChallengeRequest/ChallengeResponse`, engine challenge rounds/persistence | `test_sparse_communication_is_real_provider_work_and_plan_changes` | `SPARSE_COMMUNICATION.json` |
| F005 executable morphology | `orchestration/morphology.py`, `orchestration/dag_executor.py`, engine plan compilation/execution | `test_morphology_compiles_distinct_executable_dags`, concurrent-delay test | `MORPHOLOGY_DAG.json`, `PARALLELISM.json` |
| F006 functional plugin runtime | `plugins/api.py`, `plugins/registry.py`, `plugins/services.py`, `plugins/profiles.py`; engine consumes `RuntimeServices` | `test_plugin_runtime_services_are_functional` | `TEST_RESULTS.txt` |
| F007 execution-derived benchmark | `src/mimicus/benchmark.py`: actual A/B/C/D/E runners plus architecture-blind common grader and anti-rigging probe | benchmark integration tests and exact-head 200/arch job | `BENCHMARK_RAW.jsonl`, `BENCHMARK.json`, `BENCHMARK_ANTI_RIGGING.json` |
| F008 integrated germinal learning | `germinal/center.py`, `germinal/promote.py`, repository persisted candidates/specs/fossils, engine learn path | restart germinal promotion/reuse integration and process stages | `GERMINAL_INTEGRATED.json` |

Swarm-grade additions are also exercised by the same normal engine: deterministic semantic proximity, exact fingerprint vs lineage probation, real fan-out/fan-in, bounded async execution and critical-path telemetry. No second orchestration control plane or generated-code execution path was added.
