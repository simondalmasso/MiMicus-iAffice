# MiMicus Commercial Funnel Diagnosis V1 — Implementation Plan

## Task 1 — RED: pure diagnosis

Create:
- `core/src/mimicus/commercial/diagnosis.py`
- `core/tests/unit/test_commercial_diagnosis.py`

Tests:
- chronology errors -> DATA_QUALITY;
- proposal backlog with enough sample -> TERMINAL_STALL;
- terminal sample with low wins -> LOW_WIN_RATE;
- qualified sample with low proposal advancement -> PROPOSAL_STALL;
- QUALIFY queue -> QUALIFICATION_BACKLOG;
- sparse data -> INSUFFICIENT_DATA;
- healthy configured rates -> NO_OBSERVED_BOTTLENECK;
- input-order / mapping-order independent hash.

## Task 2 — CLI integration

Modify:
- `core/src/mimicus/interfaces/cli.py`
- `core/tests/integration/test_commercial_cli.py`

Add `--diagnose` to existing `funnel` command.
Default output remains unchanged.

## Task 3 — docs + verification

Modify:
- `docs/COMMERCIAL-DATA-CONTRACT.md`
- `STATUS.md` if branch is promoted.

Verify:
- full tests;
- coverage >= 90%;
- Ruff;
- mypy;
- package build;
- cockpit checks unchanged.

No merge or deploy until branch review is complete.
