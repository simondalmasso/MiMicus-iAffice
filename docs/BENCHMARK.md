# Benchmark

`mimicus benchmark --profile offline --episodes 200` runs a deterministic sequential fixture stream against five architectures with the same episode information:

- A — single scripted agent.
- B — static multi-agent majority/debate baseline.
- C — domain calibration/reputation routing only.
- D — falsifier market without germinal/memory immune controls.
- E — full MiMicus policy.

The report records verified final accuracy, inconclusive and repeated-error rates, falsifier reuse, false-positive/false-negative rates, false mutation promotion, evasion-farming resistance, memory-poison propagation, average agents/communication edges, simulated cost/latency, calibration/Brier behavior, fingerprint replacement transfer, and removal-style attribution where applicable.

The harness is not allowed to alter ground truth or give MiMicus extra fixture facts unavailable to a baseline. Results are evidence about this deterministic fixture distribution, not a claim of universal model superiority.

The kill question is explicit: after replacing every scripted fingerprint/model identity, does verified falsifier/fossil/provenance knowledge still reduce repeated errors? The JSON report includes before/after transfer metrics and a machine-readable answer.

The latest audited report is committed as `evidence/ORDER-002/BENCHMARK.json` with a Markdown rendering beside it. Exact-head CI reruns at least 200 episodes per architecture.
