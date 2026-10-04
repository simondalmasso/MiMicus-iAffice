# MiMicus Closer Handoff V1 — Plan

## Task 1 — RED

Add tests that prove:

- each WORK_NOW decision produces exactly one action ticket;
- HOLD/REPAIR/REJECT/COMPLETE produce no ticket;
- ticket next_action/stage/contact target match the authoritative decision/candidate;
- tickets require human approval;
- ticket hash is deterministic and changes with decision/contact semantics;
- input permutation produces the same action queue and batch hash.

## Task 2 — model + service

Modify:

- `core/src/mimicus/commercial/models.py`
- `core/src/mimicus/commercial/decision.py`

Add `CommercialActionTicket` and `LeadDecisionBatch.action_queue`.

## Task 3 — trace/cockpit

Render `next_action` in the existing `decision_emitted` Activity Stream line. JavaScript remains display-only.

## Task 4 — docs / smoke

Update architecture/runbook/status wording to describe the handoff contract.

Verify full CI:
- commercial triage smoke;
- pytest + coverage >=90%;
- Ruff;
- mypy;
- package build;
- cockpit syntax;
- Wrangler dry-run.

No deploy.
