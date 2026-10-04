# MiMicus Closeability Gate V1 — Implementation Plan

## Task 1 — RED policy tests

Extend `core/tests/unit/test_commercial_decision.py`:

- prepared below floor => HOLD;
- prepared at floor => WORK_NOW;
- replied below floor => WORK_NOW;
- contacted-due below floor => WORK_NOW;
- low prepared does not consume WIP capacity;
- policy hash changes when floor changes.

## Task 2 — GREEN model/service

Modify:

- `core/src/mimicus/commercial/models.py`
- `core/src/mimicus/commercial/decision.py`

Add `prepared_min_score` to `LeadDecisionPolicy`.

Apply the quality floor before WIP admission and only to `PREPARED`.

## Task 3 — production policy

Modify `core/config/commercial-policy-v1.json` to set an explicit floor.

Initial value is a policy choice, not a learned truth; it must remain configurable.

## Task 4 — observer contract

No new observer authority. Existing reasons should flow through `decision_emitted` automatically.

Add/update tests only if necessary to prove trace output includes the reason.

## Task 5 — verification

Run exact branch CI:

- 200+ tests PASS;
- coverage >= 90%;
- Ruff PASS;
- mypy PASS;
- package build PASS;
- cockpit syntax PASS;
- Wrangler dry-run PASS.

No deploy. No merge until exact-head is green.
