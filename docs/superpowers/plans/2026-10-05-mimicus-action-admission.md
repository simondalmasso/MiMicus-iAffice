# MiMicus Action Admission V1 — Implementation Plan

## Task 1 — RED domain tests

Create:

- `core/tests/unit/test_action_admission.py`

Test:

- explicit READ_ONLY;
- explicit MUTATING;
- unknown -> UNKNOWN;
- unknown/mutating cannot bypass effect gate;
- duplicate rules rejected;
- payload/content is not part of classification.

## Task 2 — GREEN policy primitive

Create:

- `core/src/mimicus/effects/admission.py`

Keep the implementation pure and dependency-free beyond Pydantic/stdlib already in use.

## Task 3 — MCP fail-closed integration

Modify:

- `core/src/mimicus/interfaces/mcp_server.py`
- MCP unit/integration tests as needed.

Derive `readOnlyHint` from explicit rules. Missing rule -> server construction error.

Do not alter host loopback enforcement, auth semantics, tool behavior, or persisted state.

## Task 4 — docs

Update:

- `core/docs/THREAT_MODEL.md`
- `core/docs/ARCHITECTURE.md`

Do not update `STATUS.md` until merge.

## Task 5 — verify

- focused tests;
- full pytest + coverage >=90%;
- Ruff;
- mypy;
- package build;
- cockpit syntax;
- Wrangler dry-run.

No merge/deploy in this task branch.
