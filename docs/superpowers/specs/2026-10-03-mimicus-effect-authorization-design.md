# Mimicus Effect Authorization V1 — Design

**Date:** 2026-10-03
**Branch:** `aud-arq/mimicus-effects-v1`
**Base:** `aud-arq/mimicus-scheduler-v1@55c917241fd96aa36c81f159ef9cd566a2bed8f7`

## Goal

Create an enforceable runtime effect boundary before any browser, messaging, payment, shell, filesystem or external mutation adapter is added.

## Authority

- LAYA / MiMicusEngine remains the sole orchestration authority.
- Effects are deny-by-default.
- V1 has no implicit allow path.
- A dispatch requires a durable approval receipt bound to the exact action envelope.
- The cockpit, setter ledger, model output, adapter request, or UI intent never counts as approval.

## Action envelope

Canonical frozen fields:

- `adapter`
- `operation`
- `destination`
- `resource`
- normalized JSON `payload`
- `scope`

`envelope_hash = sha256(canonical envelope)`.

Any change to destination, resource, operation, payload or scope changes the hash and invalidates approval.

## Approval receipt

Durable fields:

- `approval_id`
- `envelope_hash`
- `approver_id`
- `issued_at`
- `expires_at`
- `consumed_at` nullable
- `policy_version`

Receipt registration has no public HTTP/Worker route in V1.

## Dispatch contract

`EffectDispatcher.dispatch(envelope, approval_id, adapter)`

1. Atomically validate + consume approval in SQLite.
2. In the same durable transaction create a unique effect intent with state `AUTHORIZED`.
3. Only after transaction commit call the adapter.
4. On adapter success: mark intent `SUCCEEDED`.
5. On adapter exception/timeout: mark intent `UNKNOWN`; do not restore approval and do not auto-retry.
6. A second attempt with the same approval must be denied before adapter invocation.

## Security properties

- default configuration produces zero dispatches without approval;
- one approval authorizes one exact envelope once;
- expired approval is denied;
- tampering is denied;
- concurrent consumption yields at most one dispatch;
- unknown outcome requires reconciliation, never blind retry;
- raw credentials are not part of the envelope payload or receipts;
- no network/browser/shell implementation is introduced here.

## Storage

Add two portable SQLAlchemy tables:

`effect_approvals`
- primary key approval_id;
- envelope_hash;
- approver_id;
- issued_at;
- expires_at;
- consumed_at;
- policy_version.

`effect_intents`
- primary key intent_id;
- unique approval_id;
- envelope_hash;
- state;
- created_at;
- completed_at;
- outcome_hash nullable;
- error_class nullable.

SQLite remains baseline; schema remains PostgreSQL-compatible.

## Non-goals

- authentication UI for humans;
- remote approval endpoint;
- browser adapter;
- messaging adapter;
- credentials broker;
- distributed exactly-once across third-party systems;
- retry engine;
- OpenShell runtime dependency.

OpenShell contributes policy ideas only in V1.
