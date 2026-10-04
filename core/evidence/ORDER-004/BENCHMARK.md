# MiMicus ORDER-004 neutral execution-derived benchmark

Episodes per architecture: 200; total real architecture-runs: 1000.

| Arch | Accuracy | Inconclusive | Repeated error | Avg agents | Provider calls | Comm edges | Peak concurrency |
|---|---:|---:|---:|---:|---:|---:|---:|
| A | 0.845 | 0.150 | 0.155 | 1.00 | 1.00 | 0.00 | 1.00 |
| B | 1.000 | 0.150 | 0.000 | 3.00 | 3.00 | 0.00 | 3.00 |
| C | 0.990 | 0.150 | 0.005 | 1.00 | 1.00 | 0.00 | 1.00 |
| D | 0.925 | 0.150 | 0.075 | 1.00 | 1.00 | 0.00 | 1.00 |
| E | 0.925 | 0.150 | 0.075 | 1.30 | 1.52 | 0.23 | 2.15 |

Results are measured, not assigned. MiMicus is not claimed to dominate every metric.
Ground-truth labels are stored separately from provider inputs and are consumed only by the common post-run grader.
Anti-rigging probe: **PASS**.
