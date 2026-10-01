# Mimicus Live Commercial Observer V1 — Implementation Plan

## Task 1 — Source + observer state

Create:
- `src/mimicus/commercial/observer.py`
- `tests/unit/test_commercial_observer.py`

Behavior:
- file and HTTPS sources;
- content-hash dedupe;
- trace events from real `MiMicusEngine.triage_prospects`;
- bounded in-memory cursor buffer;
- observer errors fail open and do not invent decisions.

## Task 2 — Local HTTP read model

Create:
- `src/mimicus/interfaces/commercial_observer_server.py`
- `tests/integration/test_commercial_observer_server.py`

Behavior:
- loopback only;
- GET `/api/health`, `/api/runtime`, `/api/activity?since=N`;
- static cockpit serving;
- no mutation methods/endpoints.

## Task 3 — CLI

Modify:
- `src/mimicus/interfaces/cli.py`
- add integration tests.

Command:
`mimicus observe`.

Require:
- exactly one of `--ledger-file` or `--ledger-url`;
- `--policy-file`;
- `--cockpit-dir`;
- loopback host;
- positive poll interval.

## Task 4 — Cockpit live mode

Modify:
- root `public/app.js`.

Behavior:
- if `/api/runtime.mode == local-live-observer`, poll activity API;
- display real events;
- no duplicate decision logic;
- simulation fallback unchanged outside live mode.

## Verification

Fresh CI must pass:
- full pytest + coverage >=90%;
- ruff;
- mypy;
- build.

Adversarial:
- same ledger hash emits no duplicate decision cycle;
- malformed remote JSON cannot mutate prior state;
- observer sink failure cannot change LAYA result;
- non-loopback bind rejected;
- POST to activity API rejected;
- UI does not decide.
