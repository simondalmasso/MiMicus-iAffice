# Mimicus Effect Authorization V1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use test-driven-development / executing-plans.

**Goal:** Enforce one-use, hash-bound, durable effect approvals before adapter dispatch.

**Architecture:** Pure effect models + SQLite-backed approval/intention store + dispatcher. No real external adapter is added.

**Tech Stack:** Python, Pydantic, SQLAlchemy, existing canonical hashing.

**Spec:** `docs/superpowers/specs/2026-10-03-mimicus-effect-authorization-design.md`

## Task 1 — domain + RED

Create:
- `src/mimicus/effects/models.py`
- `tests/unit/test_effect_authorization.py`

Tests:
- default/no approval => adapter calls 0;
- exact approved envelope => one dispatch;
- payload or destination mutation => denied;
- expired => denied;
- reuse => denied.

## Task 2 — durable atomic consume

Modify:
- `src/mimicus/storage/models.py`

Create:
- `src/mimicus/effects/store.py`

Tests:
- receipt persisted;
- atomic consume creates one intent;
- two concurrent consumes of one receipt => exactly one success;
- unique approval->intent binding.

## Task 3 — dispatcher outcome semantics

Create:
- `src/mimicus/effects/dispatcher.py`

Tests:
- success => SUCCEEDED + outcome hash;
- adapter raises after invocation => UNKNOWN;
- UNKNOWN receipt remains consumed;
- second call does not invoke adapter.

## Task 4 — service seam + verification

Modify:
- `src/mimicus/plugins/services.py`
- `src/mimicus/plugins/profiles.py`
- plugin tests.

Mount `effect_dispatch` but no adapter capabilities.

Verify full suite, coverage >=90%, Ruff, mypy, build.
