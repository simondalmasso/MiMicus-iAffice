# Zero-cost guard

`COST_HARD_CAP_USD=0`. AriaOS requires no paid API, VPS, SaaS, model fallback, card trial, automatic plan upgrade, ad budget, purchase or payment.

Operational caps are deliberately below Free allocations: Workers 70k/85k requests; D1 reads 3.5m/4.25m; D1 writes 65k/80k; Queue operations 6.5k/8k; Workflow steps 2k/2.4k; Workers AI neurons 7.5k/8.5k. `BudgetGovernor` rejects configured hard caps above 85% of the verified Free limit.

At soft cap optional model/research work defers. At hard cap non-critical usage throws before consumption. No paid failover exists. Persisted task/cursor/deferred state prevents silent data loss.
