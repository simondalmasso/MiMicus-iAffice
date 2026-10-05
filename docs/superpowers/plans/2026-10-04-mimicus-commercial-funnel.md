# MiMicus Commercial Funnel V1 — Plan

## Task 1 — RED: pure funnel analytics

Create:
- `core/src/mimicus/commercial/funnel.py`
- `core/tests/unit/test_commercial_funnel.py`

Test:
- aggregate current stage/disposition/action counts;
- terminal win-rate semantics;
- qualified->proposal and proposal->terminal transition counts/rates;
- median stage latency;
- future evidence exclusion;
- invalid timestamp order;
- sanitized calibration rows;
- input/batch mismatch fail-closed;
- input permutation gives identical dump/hash.

## Task 2 — engine seam

Add:
- `MiMicusEngine.commercial_funnel(...)`

It must call the existing commercial decision service once, then build the snapshot from the same normalized candidates + authoritative batch.

No provider/telemetry/effect mutation.

## Task 3 — read-only CLI

Add:
- `mimicus funnel --ledger-file ... --policy-file ... --as-of ...`

Output JSON only. No writes.

## Task 4 — fixture/release smoke

Extend the sanitized commercial demo fixture to include evidenced qualified/proposal/won/lost records without private buyer text.

CI smoke must prove:
- proposal remains WORK_NOW;
- terminal funnel metrics are deterministic;
- no private evidence content appears in funnel output.

## Task 5 — full verification

- pytest + coverage >=90%;
- Ruff;
- mypy;
- package build;
- cockpit JS syntax;
- Wrangler dry-run.

No deploy.
