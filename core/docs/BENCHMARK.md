# ORDER-003 execution-derived benchmark

The V0.2 benchmark replaces the historical ORDER-002 architecture-scripted outcome generator. ORDER-002 benchmark files remain provenance evidence, but they are not evidence that MiMicus outperformed alternative architectures.

ORDER-003 executes five actual runner implementations against the same ordered deterministic public fixture stream:

- A: one provider agent.
- B: static three-agent majority.
- C: direct-calibration router.
- D: provider agent plus the safe falsifier market, without persistent immune/germinal controls.
- E: the full MiMicus V0.2 runtime.

Ground truth is stored separately from public provider input. A single `common_grade(fixture, actual_runner_output)` function grades every architecture only after the runner returns. The grader has no architecture argument. Agent counts, provider calls, communication edges, falsifier executions, state transitions, work/critical steps, concurrency, cost, replay state and latency come from the actual run output or measured execution rather than architecture-name formulas.

The required exact-head run executes at least 200 fixtures for each architecture, at least 1,000 architecture-runs total, and commits `BENCHMARK_RAW.jsonl` plus aggregate JSON/Markdown.

Anti-rigging evidence intentionally degrades E's provider on a fixture and verifies the common metric falls, then improves a baseline provider and verifies that baseline metric rises. This is a structural check against a benchmark that simply assigns a predetermined winner.

Default provider accounting is deterministic/simulated unless a live provider is explicitly substituted. Timing from CI is measured runtime evidence and may vary between machines. The report does not claim that E must dominate every metric.
