# MiMicus Commercial Intervention V1 — Design

**Date:** 2026-10-06  
**Branch:** `aud-arq/mimicus-commercial-intervention-v1`  
**Base:** `main@2fafc150a3d2341fd562e3754a417ad20e7c8d8b`

## Problem

MiMicus can now:

- select commercial work;
- create measurable closer action tickets;
- measure the funnel;
- diagnose the current bottleneck.

The diagnosis is still observational. It does not produce a canonical, measurable intervention contract.

## Goal

Derive one deterministic, zero-cost `CommercialInterventionPlan` from:

- `CommercialFunnelDiagnosis`;
- the explicit `CommercialDiagnosisPolicy`.

The plan describes what to improve and the exact metric criteria that prove improvement.

It is not permission to send, mutate CRM state, change ranking, or alter commercial stage.

## Intervention codes

- `REPAIR_STAGE_EVIDENCE`
- `QUALIFY_BACKLOG`
- `ADVANCE_QUALIFIED_TO_PROPOSAL`
- `RESOLVE_PROPOSALS`
- `IMPROVE_TERMINAL_WIN_RATE`
- `COLLECT_FULL_FUNNEL_EVIDENCE`
- `MAINTAIN_BASELINE`

## Success criteria

A criterion is frozen and structured:

- `metric`
- `comparator` = `eq|lt|lte|gte`
- `target`
- `baseline`

No hidden thresholds are introduced. Targets come from the explicit diagnosis policy:

- data quality: `invalid_order_count == 0`;
- terminal stall: `proposal_to_terminal_rate >= min_transition_rate`;
- low win rate: `terminal_win_rate >= min_terminal_win_rate`;
- proposal stall: `qualified_to_proposal_rate >= min_transition_rate`;
- qualification backlog: `qualify_count < min_qualify_backlog`;
- insufficient data: collect configured minimum sample counts;
- no bottleneck: maintain configured sample and rate thresholds.

## Hash contract

`intervention_hash` binds:

- diagnosis hash;
- diagnosis policy hash;
- bottleneck;
- intervention code;
- focus;
- criteria.

Input ordering must not affect the hash.

## Authority boundary

The plan:

- does not mutate `LeadDecisionPolicy`;
- does not modify `CommercialActionTicket`;
- does not change WIP/ranking/disposition;
- does not invoke a provider/model;
- does not create an effect approval;
- does not send messages;
- is read-only analytical output.

## CLI

`mimicus funnel ... --diagnose --intervene`

returns:

```json
{
  "snapshot": {...},
  "diagnosis": {...},
  "intervention": {...}
}
```

`--intervene` without `--diagnose` is rejected.

## Non-goals

- message drafting;
- sales-copy generation;
- autonomous policy tuning;
- learned ranking;
- automatic experiment execution;
- auto-send.
