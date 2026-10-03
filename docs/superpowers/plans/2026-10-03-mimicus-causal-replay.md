# Mimicus Causal Replay V1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use test-driven-development / executing-plans.

**Goal:** Add a semantic causal DAG contract to the existing replay machinery while explicitly excluding incidental runtime metadata.

**Architecture:** A pure `causal_replay.py` builds/verifies canonical DAG semantics from MorphologyPlan + DagExecution. Legacy execution records it; production semantic replay V2 verifies it offline.

**Tech Stack:** Python, Pydantic/dataclasses already present, existing canonical SHA-256.

**Spec:** `docs/superpowers/specs/2026-10-03-mimicus-causal-replay-design.md`

## Task 1 — pure causal record

Create:
- `src/mimicus/orchestration/causal_replay.py`
- `tests/unit/test_causal_replay.py`

RED:
- build from small successful DAG;
- different incidental run IDs/timing/scheduler metadata => identical semantic hash;
- prerequisite/output tamper => verify false;
- duplicate/missing prerequisite/cycle => false.

## Task 2 — runtime capture

Modify:
- `src/mimicus/orchestration/legacy_engine.py`

Add `causal_execution` to RunResult.
After successful DagExecutor execution, build causal record and bind its hash into `dag_execution_completed` ledger payload.

Tests:
- normal run exposes causal record;
- all causal nodes correspond to plan nodes;
- precompleted nodes are represented.

## Task 3 — semantic replay V2

Modify:
- `src/mimicus/orchestration/production_core.py`
- `src/mimicus/orchestration/semantic_replay.py`
- existing F044 integration tests.

V2 input material includes causal semantic record.
Expected includes causal hash.
Replay returns `causal_contract_verified`.
Causal tampering must fail.
Existing V1 snapshot shape remains supported.

## Task 4 — injectable event metadata

Modify:
- `src/mimicus/events/ledger.py`
- `tests/unit/test_ledger_storage_security.py`

Injectable aware clock + ID source; defaults unchanged.
Tests prove event metadata can differ while causal semantic hash remains unaffected.

## Task 5 — full verification

Run full suite, coverage >=90%, Ruff, cockpit JS syntax, mypy, build.
No merge/deploy.
