# MiMicus Action Admission V1 — Design

**Role:** ARQ  
**Base SHA:** `6b0c5726c27e5e8d4b907f7175c93caaa1396e97`  
**Branch:** `arq/effects-tool-admission-v1`

## Objective

Add one small source-controlled action-classification boundary before future browser/computer/outreach tooling is introduced.

The invariant is:

> An operation may bypass the effect gate only when MiMicus explicitly classifies the exact adapter + operation pair as `READ_ONLY`.

Anything mutating or unclassified fails dangerous:

- `MUTATING` -> cannot bypass the effect gate;
- `UNKNOWN` -> cannot bypass the effect gate.

No browser, messaging, shell, payment, filesystem mutation or other real-world adapter is added by this work.

## Model

`ToolEffectClass`:

- `READ_ONLY`
- `MUTATING`
- `UNKNOWN`

`ActionAdmissionRule` binds:

- `adapter`
- `operation`
- `effect_class`

`ActionAdmissionPolicy`:

- contains exact source-controlled rules;
- rejects duplicate adapter/operation rules;
- ignores payload text for classification;
- returns `UNKNOWN` for any unmatched action;
- exposes `may_bypass_effect_gate=True` only for explicit `READ_ONLY`.

No wildcard rules in V1.

## MCP integration

The current MCP tool surface already has a transport boundary: mutating HTTP exposure is loopback-only.

V1 uses the same action-classification primitive to derive the MCP `readOnlyHint` for the three current tools:

- `get_mimicus_run` -> `READ_ONLY`;
- `run_mimicus` -> `MUTATING`;
- `submit_verification` -> `MUTATING`.

A future MCP tool without an explicit rule must fail server construction rather than silently inherit a read-only annotation.

This classification does **not** replace transport authentication or `EffectApprovalReceipt`. MCP local-state mutation remains governed by its existing transport and server-side policy boundaries.

## Authority

- LAYA / `MiMicusEngine` remains the only orchestration authority.
- `EffectDispatcher` remains the only existing external-effect dispatch boundary.
- This work does not create an alternative dispatcher.
- No provider/commercial/cockpit/CI/release contract changes.

## Acceptance

1. unknown action cannot bypass effect gate;
2. explicit mutating action cannot bypass effect gate;
3. explicit read-only action can;
4. duplicate/conflicting exact rules are rejected;
5. MCP annotations are derived from explicit rules;
6. unknown MCP tool classification fails closed;
7. full repository CI passes;
8. no deployment and no real-world effects.
