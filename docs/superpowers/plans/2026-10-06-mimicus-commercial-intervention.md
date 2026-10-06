# MiMicus Commercial Intervention V1 — Plan

## Task 1 — RED

Create unit tests that prove:

- every bottleneck maps to exactly one intervention code;
- targets are derived from explicit diagnosis policy values;
- baseline metrics are carried from the diagnosis;
- plan hash is canonical;
- no diagnosis policy threshold is silently invented.

## Task 2 — GREEN

Create:

- `core/src/mimicus/commercial/intervention.py`

Models:

- `CommercialInterventionCode`
- `CommercialMetricCriterion`
- `CommercialInterventionPlan`

Function:

- `plan_commercial_intervention(diagnosis, policy)`

## Task 3 — CLI

Extend `mimicus funnel` with `--intervene`.

Requirements:

- `--intervene` requires `--diagnose`;
- default funnel output remains unchanged;
- diagnose-only output remains unchanged.

## Task 4 — docs + verification

Update:

- commercial data contract;
- architecture/status checkpoint;
- package exports.

Run exact branch CI:

- locked install + pip check;
- full tests/coverage >=90%;
- Ruff;
- mypy;
- build;
- cockpit gates.

No merge/deploy until green.
