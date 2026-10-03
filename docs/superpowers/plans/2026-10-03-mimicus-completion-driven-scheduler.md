# Mimicus Completion-Driven DAG Scheduler V1 — Implementation Plan

## Task 1 — RED: characterize barrier defect

Modify:
- `archive/MiMicus-swarm-source/tests/unit/test_order004_correctness.py`

Add event-controlled test:
- A and B start from precompleted root.
- B remains blocked.
- release A.
- assert A1 starts before B release.
- release B for cleanup.

No timing threshold is an assertion.

## Task 2 — GREEN: replace batch barrier

Modify:
- `archive/MiMicus-swarm-source/src/mimicus/orchestration/dag_executor.py`

Implement deterministic ready queue + `in_flight` map + `asyncio.wait(FIRST_COMPLETED)`.

On any fatal task failure:
- cancel all in-flight siblings;
- await cancellation;
- record started-node statuses;
- raise `DagExecutionError`.

Do not alter plan compiler, handler API, node timeout semantics, or output hashes.

## Task 3 — regression/falsification

Verify:
- new event-controlled descendant test;
- existing structured cancellation test;
- all five morphologies runtime reachable;
- full test suite;
- coverage >=90%;
- Ruff;
- mypy;
- build;
- live cockpit JS syntax.

## Acceptance

- A1 can start while unrelated B is still in flight.
- A1 cannot start before A completes successfully.
- peak concurrency never exceeds limit.
- fatal node cancels in-flight siblings.
- all existing tests green.
- no dependency added.
- no merge/deploy.
