# MiMicus ORDER-003 execution-derived benchmark

Episodes per architecture: 200; total real architecture-runs: 1000.

| Arch | Accuracy | Inconclusive | Repeated error | Avg agents | Provider calls | Comm edges | Peak concurrency |
|---|---:|---:|---:|---:|---:|---:|---:|
| A | 0.905 | 0.150 | 0.091 | 1.00 | 1.00 | 0.00 | 1.00 |
| B | 0.980 | 0.150 | 0.021 | 3.00 | 3.00 | 0.00 | 3.00 |
| C | 0.915 | 0.150 | 0.091 | 1.00 | 1.00 | 0.00 | 1.00 |
| D | 1.000 | 0.150 | 0.000 | 1.00 | 1.00 | 0.00 | 1.00 |
| E | 0.985 | 0.150 | 0.016 | 1.00 | 1.00 | 0.00 | 1.85 |

Results are measured, not assigned. MiMicus is not claimed to dominate every metric.
Ground-truth labels are stored separately from provider inputs and are consumed only by the common post-run grader.
Anti-rigging probe: **PASS**.
