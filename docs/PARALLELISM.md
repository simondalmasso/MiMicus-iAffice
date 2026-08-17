# Parallel execution and critical-path telemetry

MiMicus V0.2 is async-first internally. `MiMicusEngine.run_async()` executes the compiled Morphology DAG with `DagExecutor`; `run()` remains a synchronous compatibility wrapper.

Independent ready nodes may overlap, bounded by `max_concurrency` in the safe range 1..8. Agent provider calls use native async adapters. Deterministic falsifiers can occupy independent DAG nodes. JOIN nodes wait only for declared predecessors. Node timeouts fail explicitly; the executor does not leave uncontrolled background tasks after completion.

The runtime records execution-derived metrics inspired by critical-path analysis:

- `work_steps`: logical work across completed nodes.
- `critical_steps`: longest prerequisite-path logical step count.
- `critical_path_ms`: longest measured dependency-path duration.
- `observed_wall_ms`: end-to-end executor wall duration.
- `serial_work_ms`: sum of measured node work durations.
- `peak_concurrency`: maximum simultaneously executing nodes.
- `parallel_speedup_estimate`: serial work divided by observed wall time.
- `parallel_efficiency`: speedup divided by peak concurrency, bounded to 1.
- `subtask_finish_rate`: completed agent/falsifier/challenge subtasks divided by planned such subtasks.
- `avoidable_serialization_count`: ready independent work left serial when concurrency capacity was available.

The ORDER-003 process E2E uses two independent scripted nodes with approximately 250 ms delays and requires wall time below 425 ms, retained output hashes, `critical_path_ms < serial_work_ms`, `peak_concurrency >= 2`, and zero avoidable serialization when capacity is two.

Budget reservation is guarded before provider work starts so concurrent scheduling cannot silently exceed the configured run budget. Timings are audit evidence, not deterministic replay keys.
