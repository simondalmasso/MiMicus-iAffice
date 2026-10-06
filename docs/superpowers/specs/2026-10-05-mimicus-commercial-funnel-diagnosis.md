# MiMicus Commercial Funnel Diagnosis V1 — Design

**Date:** 2026-10-05
**Branch:** `aud-arq/mimicus-commercial-diagnosis-v1`
**Base:** `main@47cae3d1343f2b93d733930944b6ed00912fdffc`

## Problem

MiMicus already:
- selects commercial work deterministically;
- creates auditable closer action tickets;
- records evidence-backed commercial stages;
- measures funnel transitions.

But the funnel snapshot is descriptive only. It does not identify the most likely operational bottleneck.

## Goal

Add a deterministic, zero-cost, read-only diagnosis over `CommercialFunnelSnapshot`.

The diagnosis:
- never changes LAYA ranking or disposition;
- never calls a model/provider;
- never mutates setter data;
- never sends a message;
- never creates an effect approval;
- is fully determined by the snapshot plus an explicit diagnosis policy.

## Policy

`CommercialDiagnosisPolicy` contains explicit thresholds:

- `min_transition_samples`
- `min_terminal_samples`
- `min_transition_rate`
- `min_terminal_win_rate`
- `min_qualify_backlog`

Thresholds are configuration, not hidden heuristics.

## Bottleneck classes

- `DATA_QUALITY` — invalid commercial stage chronology exists.
- `TERMINAL_STALL` — enough proposals exist, but too few reach won/lost.
- `LOW_WIN_RATE` — enough terminal outcomes exist, but too few are won.
- `PROPOSAL_STALL` — enough qualified leads exist, but too few reach proposal.
- `QUALIFICATION_BACKLOG` — a material number of current actions are QUALIFY and there is not yet stronger transition evidence.
- `INSUFFICIENT_DATA` — not enough evidence to identify a bottleneck.
- `NO_OBSERVED_BOTTLENECK` — enough evidence exists and configured thresholds are met.

Priority is deterministic in the order above, except `LOW_WIN_RATE` is evaluated after proposal-to-terminal progression so "no terminal outcomes" is not mislabeled as a win-rate problem.

## Diagnosis artifact

Frozen fields:

- `snapshot_hash`
- `policy_hash`
- `bottleneck`
- `reasons`
- `focus`
- `supporting_metrics`
- `diagnosis_hash`

The hash binds all semantic diagnosis fields except itself.

No buyer/title/URL/evidence free text is included.

## CLI

Existing `mimicus funnel` remains backward-compatible.

New optional flag:

`mimicus funnel ... --diagnose`

Without the flag: existing snapshot JSON.

With the flag:

```json
{
  "snapshot": {...},
  "diagnosis": {...}
}
```

## Non-goals

- auto-changing lead policy;
- learned ranking;
- LLM sales coaching;
- message drafting;
- auto-send;
- CRM mutation;
- inventing missing timestamps/stages.
