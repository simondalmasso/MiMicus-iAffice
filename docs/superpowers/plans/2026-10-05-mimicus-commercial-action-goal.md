# MiMicus Commercial Action Goal V1 — Plan

## Task 1 — RED
Add unit tests proving deterministic goal mapping for CONTACT, QUALIFY, PROPOSE and both FOLLOW_UP cases.

## Task 2 — model/service
Add `CommercialGoalCode`, `CommercialActionGoal`, and derive it while creating `CommercialActionTicket`.

## Task 3 — hash/authority
Bind goal into ticket hash; prove source input cannot directly set goal and human approval remains required.

## Task 4 — docs + gates
Update `docs/COMMERCIAL-DATA-CONTRACT.md`.
Run PR CI: commercial smokes, full pytest/coverage, Ruff, mypy, build, cockpit dry-run.
No deploy.
