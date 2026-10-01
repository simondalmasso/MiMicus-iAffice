# Mimicus Lead Decision Gate V1 — Design Specification

**Date:** 2026-10-01  
**Branch:** `aud-arq/mimicus-lead-decision-v1`  
**Base:** `mimicus-v2-monochrome@f9d185203e5ab9362a56dda2dcd7fd38e39db22f`  
**Status:** DESIGN — approved direction, implementation not yet started

## 1. Purpose

The Facebook and Reddit setters are producing usable prospect volume, but prospecting quality is not translating into closed work yet.

The immediate architecture goal is therefore not "find more leads." It is to insert a **deterministic decision gate under LAYA** between setter discovery and commercial action.

The system must answer:

> Of all current prospects found by the setters, which few deserve attention now, which should wait, which require data repair, and which should be rejected?

The gate must improve prioritization without becoming a second control plane and without introducing a paid dependency.

## 2. Current evidence

Current canonical setter state lives on `main` in:

- `SETTERS.md`
- `data/gpt-prospectos.json`

Observed on 2026-10-01:

- 14 total prospect records;
- Facebook: 9 total, 7 active;
- Reddit: 5 total, 3 active;
- 11 records have reached `contacted`, `replied`, or `closed`;
- 1 record is currently `replied`;
- current schema has no explicit `won` / `lost` commercial outcome;
- `closed` is therefore not safe to interpret as either success or failure.

The observed reply fraction among the 11 progressed records is approximately 9.09%. Zero explicit wins does not justify estimating a true zero close probability from this small sample.

This V1 therefore **must not train a learned close-probability model** from the current data.

## 3. Architectural decision

### 3.1 One authority

LAYA / `MiMicusEngine` remains the only orchestration authority.

The new component is subordinate:

```text
Facebook Setter ─┐
                 ├─> canonical prospect ledger
Reddit Setter ───┘
                         │
                         v
                 Prospect Ingest Adapter
                         │
                         v
                Lead Decision Service
                 deterministic baseline
                         │
                         v
                     LAYA
                final queue ownership
                         │
                ┌────────┴────────┐
                v                 v
           WORK NOW             HOLD
                │
                v
       future authorized action
```

The decision service recommends. LAYA owns the final work queue.

No external model, vector database, SaaS, browser agent, or scoring framework may acquire execution authority.

### 3.2 V1 is a queue governor, not an ML predictor

V1 will not pretend to know calibrated close probabilities.

It will produce a stable ordering and explicit disposition from structured evidence.

Primary output:

- `WORK_NOW`
- `HOLD`
- `REPAIR_DATA`
- `REJECT`

Each decision also carries:

- deterministic rationale;
- normalized features used;
- data-quality issues;
- decision hash;
- source prospect ID;
- lane;
- rank position inside the lane.

## 4. Commercial policy

### 4.1 Lane ownership

Existing ownership remains unchanged:

- Facebook setter owns Facebook discovery/follow-up.
- Reddit setter owns Reddit discovery/follow-up.
- LAYA owns cross-lane prioritization and final attention allocation.

### 4.2 WIP

Default active work limit:

- maximum 3 selected prospects per lane.

This is a policy value, not hard-coded business truth. It must be configurable through an immutable policy object used by the decision run.

### 4.3 Stage precedence

V1 uses lexicographic precedence rather than an invented probability formula.

Default stage order:

1. `replied`
2. `prepared`
3. `contacted_due`
4. `contacted_waiting`

Terminal `closed` records are excluded from active selection.

A setter's existing `rank.score` may be used only as a late tie-breaker. It cannot override stage, hard eligibility, risk, or data-quality policy.

Within the same stage, V1 tie-break order is:

1. lower scam risk (`low` before `medium`);
2. complete action metadata before incomplete action metadata;
3. higher setter `rank.score`;
4. newer `verifiedAt`;
5. stable lexical `prospect_id` as the final deterministic tie-breaker.

### 4.4 Hard eligibility

A prospect must not enter `WORK_NOW` when a binding hard failure is known, including:

- `active=false`;
- `argentinaEligible=false`;
- `workerFee=true` where the lane forbids pay-to-apply;
- `scamRisk=high`;
- terminal status.

Existing open leads are not invalidated merely because their original publication is now older than 48 hours. The 48-hour rule applies to admission of new prospects, matching the existing setter contract.

### 4.5 Data-quality fail-closed behavior

Missing fields must not be silently synthesized.

Important V1 cases:

- contacted lead with missing `contactedAt`:
  - do not invent follow-up timing;
  - emit `REPAIR_DATA`;
- missing exact `sourceUrl` / `directUrl`:
  - no external action;
- missing identifiable buyer when the admission contract requires one:
  - no external action;
- unknown commercial outcome:
  - never map automatically to won/lost.

## 5. Decision representation

New Python domain types should live under a focused commercial package, for example:

```text
src/mimicus/commercial/
    __init__.py
    models.py
    prospect_ingest.py
    decision.py
```

### 5.1 LeadCandidate

Normalized, immutable Pydantic model derived from the setter ledger.

Minimum fields:

- `prospect_id`
- `source_name`
- `lane`
- `buyer`
- `title`
- `active`
- `argentina_eligible`
- `worker_fee`
- `scam_risk`
- `setter_score`
- `outreach_status`
- `published_at`
- `verified_at`
- `contacted_at`
- `source_url`
- `direct_url`

The adapter may preserve extra source evidence separately, but decision logic must not depend on parsing free-form prose such as `rank.reason`.

### 5.2 LeadDecisionPolicy

Frozen configuration containing:

- `max_work_per_lane=3`
- stage precedence;
- hard-reject rules;
- required explicit follow-up timing thresholds by channel (no hidden wall-clock default inside the service);
- tie-break order;
- policy version.

The complete policy participates in the decision hash.

### 5.3 LeadDecision

Minimum result:

- `prospect_id`
- `lane`
- `disposition`
- `stage`
- `rank_position`
- `reasons`
- `data_quality_issues`
- `input_hash`
- `policy_hash`
- `decision_hash`

### 5.4 LeadDecisionBatch

Contains:

- all input prospect IDs;
- every individual decision;
- selected IDs by lane;
- held IDs;
- rejected IDs;
- repair-data IDs;
- deterministic batch hash.

Input order must not affect the resulting batch hash or ranking when prospect content is identical.

## 6. LAYA integration boundary

A generic external "Decide" model is **not** the V1 authority.

The preferred seam is a runtime service, conceptually:

```python
class LeadDecisionService(Protocol):
    def decide(
        self,
        candidates: list[LeadCandidate],
        policy: LeadDecisionPolicy,
        *,
        as_of: datetime,
    ) -> LeadDecisionBatch: ...
```

Baseline implementation:

`DeterministicLeadDecisionService`

LAYA / `MiMicusEngine` receives the batch and owns the commercial work queue.

A future model-backed provider may run in **shadow mode only**:

```text
deterministic decision ---> authoritative
        |
        +-- shadow provider ---> comparison/eval only
```

Shadow output cannot alter:

- selection;
- memory authority;
- ledger state;
- effects;
- WIP;
- follow-up action.

Promotion requires an explicit benchmark and separate architectural approval.

## 7. Outcome feedback

Closing performance cannot improve if the schema records only `closed`.

A future compatible extension to the setter ledger should add an optional outcome object:

```json
{
  "outcome": {
    "status": "pending | won | lost | no_response | declined | not_fit | unknown",
    "reason": null,
    "resolvedAt": null,
    "value": null,
    "currency": null
  }
}
```

V1 reader must work when `outcome` is absent.

No current setter file on `main` is modified by this branch while setters are working.

Once enough resolved outcomes exist, they may be used for evaluation/calibration. They do not automatically authorize online learning.

## 8. Side-effect boundary

This subproject performs no outreach.

Explicitly forbidden in V1 decision execution:

- send message;
- submit comment;
- DM;
- email;
- browser submit;
- payment;
- mutation of Facebook/Reddit;
- mutation of canonical setter ledger.

The result is a recommendation artifact only.

Future action execution must pass the separate Mimicus effect-authorization architecture:

`EffectPolicy -> bound approval receipt -> durable intent -> dispatch`

That subsystem is not implemented as part of this spec.

## 9. Scheduler, effects, replay: separate workstreams

Astra's three architecture findings are accepted as independent work:

1. completion-driven `DagExecutor` scheduling;
2. enforced effect authorization;
3. causal replay contract.

They are deliberately excluded from Lead Decision Gate V1 so the commercial filter can ship and be evaluated without changing canonical DAG scheduling or effect semantics at the same time.

This prevents a failed scheduler refactor from blocking lead triage.

## 10. Persistence

V1 requires no new database.

Baseline:

- setter source remains the canonical JSON ledger on `main`;
- Mimicus decision execution is pure/deterministic from normalized input + policy + explicit `as_of`;
- tests use fixtures;
- optional decision receipts may later be persisted through existing SQLite repository seams.

No PostgreSQL, Convex, InsForge, LanceDB, Graphiti, or new hosted database is required.

## 11. External frameworks

Not required for V1:

- LangGraph
- CrewAI
- AutoGen
- PydanticAI as an orchestrator
- Dify
- Mastra
- Agno
- Semantic Kernel / Microsoft Agent Framework
- n8n
- InsForge
- Convex
- LanceDB
- Temporal
- Langfuse
- DeepEval
- Browser Use
- E2B
- Floot

The absence of these dependencies is intentional.

The feature is small enough to implement with the existing Python/Pydantic stack and Mimicus service seams.

## 12. Determinism

Decision determinism means:

same normalized candidates
+ same policy
+ same explicit `as_of`
= same decisions and hashes.

The implementation must not call:

- `datetime.now()` inside ranking logic;
- `uuid4()` inside ranking logic;
- random generators;
- network services;
- LLMs.

Time is an explicit input.

## 13. Acceptance criteria

### Functional

1. Every active Facebook/Reddit candidate supplied to the service receives exactly one decision.
2. No lane returns more than `max_work_per_lane` `WORK_NOW` records.
3. `replied` outranks `prepared`, which outranks due follow-up, which outranks waiting contact.
4. `closed` cannot enter `WORK_NOW`.
5. Hard-ineligible records cannot enter `WORK_NOW`.
6. Missing `contactedAt` is not interpreted as an invented due date.
7. Setter score cannot override a hard rule.
8. Input list permutation does not change authoritative ranking/hashes.
9. Same `as_of` gives byte-stable serialized decision output.
10. No external action occurs.

### Architectural

11. `MiMicusEngine` remains the single orchestration authority.
12. Decision logic is exposed through a replaceable service seam.
13. Baseline requires no SaaS and no model tokens.
14. A shadow decision provider cannot mutate authoritative results.
15. Existing memory/provenance/effect authority is unchanged.

### Regression

16. Existing Mimicus unit/integration suites remain green.
17. Coverage remains at or above the repository's 90% gate.
18. Existing setter files on `main` are not modified in this branch.

## 14. Required focused tests

At minimum:

- replied vs prepared priority;
- per-lane WIP cap;
- closed exclusion;
- scam-risk hard rejection;
- worker-fee hard rejection;
- Argentina eligibility hard rejection;
- missing-contactedAt repair behavior;
- old-but-valid open lead not killed by 48-hour admission rule;
- input-order invariance;
- deterministic batch hash;
- shadow provider cannot affect authoritative batch;
- zero-side-effect fake adapter observation.

Tests should assert public decision behavior, not duplicate the sorting implementation.

## 15. Rollout

### Phase A — pure domain slice

Add models, deterministic decision service and unit tests only.

No engine integration yet.

### Phase B — LAYA seam

Mount the service through the existing runtime-service pattern and expose an internal engine method for prospect triage.

No external effects.

### Phase C — current-ledger adapter

Add a read-only adapter that can normalize the canonical prospect JSON schema.

Do not write the ledger.

### Phase D — shadow evaluation

Replay historical/current ledger snapshots and compare the authoritative policy against future experimental providers.

No promotion without measured benefit.

### Phase E — outcome instrumentation

After coordination with both setter workers, extend the canonical ledger schema with explicit outcomes and begin measuring:

- reply rate;
- qualified-reply rate;
- won rate;
- time-to-reply;
- time-to-close;
- false-priority rate;
- opportunity cost from held leads.

## 16. Rollback

Every phase is removable.

If the decision gate misbehaves:

- disable engine integration;
- setters continue using their existing ledger and workflow;
- no data migration is required;
- no external state has been mutated.

## 17. Non-goals

This spec does not:

- redesign the cockpit;
- replace setters;
- autonomously send outreach;
- add a remote Worker-to-LAYA command bridge;
- train an ML model;
- claim calibrated close probabilities;
- add a graph/vector database;
- add another agent framework;
- merge PR #9;
- modify setter `main` state;
- deploy production.

## 18. Open but non-blocking questions

These do not block V1 pure-domain implementation:

- production follow-up delay by channel; the pure decision service receives this explicitly through policy and does not invent a default;
- whether future cross-lane global WIP should be lower than 6 total;
- eventual commercial-value weighting after explicit won/lost data exists;
- whether a local model can outperform deterministic policy in shadow mode.

They must be evaluated from outcomes, not guessed into V1.

## 19. Decision summary

The implementation target is:

```text
SETTERS
   |
   v
CANONICAL LEDGER
   |
   v
NORMALIZE
   |
   v
DETERMINISTIC LEAD DECISION SERVICE
   |
   v
LAYA / MiMicusEngine
   |
   +--> WORK NOW (max 3/lane)
   +--> HOLD
   +--> REPAIR DATA
   +--> REJECT

No send.
No SaaS.
No second control plane.
No fake probability model.
```
