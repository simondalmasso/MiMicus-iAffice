# MiMicus Commercial Stage Evidence V1 — Plan

## Task 1 — RED

Extend commercial decision tests:

- qualified without matching evidence -> REPAIR_DATA;
- proposal with only qualification evidence -> REPAIR_DATA;
- matching proposal evidence -> proposal priority/next action;
- future-dated matching evidence -> REPAIR_DATA;
- won/lost require matching outcome evidence before COMPLETE;
- legacy unknown-stage leads remain unchanged.

## Task 2 — model + ingest

Modify:

- `core/src/mimicus/commercial/models.py`
- `core/src/mimicus/commercial/prospect_ingest.py`

Add frozen stage evidence and preserve tuple ordering deterministically.

## Task 3 — decision gate

Modify:

- `core/src/mimicus/commercial/decision.py`

Validate elevated stage evidence before commercial stage is allowed to influence ranking or terminal completion.

## Task 4 — trace/tests/docs

Verify evidence-backed progression through engine/trace contracts. Run full MiMicus CI:

- pytest + coverage >=90%;
- Ruff;
- mypy;
- package build;
- cockpit syntax;
- Wrangler dry-run.

No merge/deploy until green.
