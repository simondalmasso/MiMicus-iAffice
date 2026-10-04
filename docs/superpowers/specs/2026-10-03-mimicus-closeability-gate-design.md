# MiMicus Closeability Gate V1 — Design

**Date:** 2026-10-03  
**Branch:** `aud-arq/mimicus-closeability-gate-v1`  
**Base:** `main@a4845a829827d7a9d2b653a1ee37ede164868077`

## Problem

The commercial gate already rejects unsafe/ineligible leads and prioritizes by outreach stage, but any structurally valid `prepared` lead can consume `WORK_NOW` capacity when a lane has free slots, even when its setter score is weak.

That is a WIP-allocation defect: scarcity is enforced, but minimum quality for untouched prepared work is not.

## Goal

Add a deterministic quality floor for **prepared, not-yet-contacted** prospects.

The rule must:

- remain inside `LeadDecisionPolicy` / `DeterministicLeadDecisionService`;
- require no model call, network call or new dependency;
- preserve LAYA as the only commercial decision authority;
- never block an actual reply;
- never block a follow-up that is already due merely because the original setter score was low;
- keep low-quality prepared leads visible as `HOLD`, not silently delete or reject them;
- be fully hash-bound through the existing policy and decision hashes.

## Policy

Add:

```text
prepared_min_score: float  # 0..100
```

Default: `0` for backward-compatible API semantics.

The repository policy `core/config/commercial-policy-v1.json` sets an explicit production value.

## Decision rule

For an otherwise eligible candidate:

1. Existing hard rejection/data-repair rules run first.
2. Existing stage precedence remains unchanged.
3. `CONTACTED_WAITING` remains `HOLD`.
4. `PREPARED` with `setter_score < prepared_min_score` remains `HOLD` with reason:
   `prepared_below_quality_floor`.
5. `REPLIED` is never blocked by this floor.
6. `CONTACTED_DUE` is never blocked by this floor.
7. Only candidates that survive the above may consume lane WIP.

## Why not a new "AI closeability scorer"

The current setter score is already an input signal. Adding another model would add cost, nondeterminism and a second opaque scoring surface without evidence that it improves outcomes.

This change fixes WIP admission using the information already present.

## Falsifiers

The implementation fails if any of these are true:

- a prepared lead below the configured floor becomes `WORK_NOW`;
- a replied lead below the floor is held solely because of score;
- a due follow-up below the floor is held solely because of score;
- a held low-score prepared lead consumes lane capacity;
- identical inputs/policy/as_of produce different hashes;
- changing the floor does not change the policy hash.
