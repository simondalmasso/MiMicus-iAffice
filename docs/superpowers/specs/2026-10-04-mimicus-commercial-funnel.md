# MiMicus Commercial Funnel V1 — Design

**Date:** 2026-10-04
**Branch:** `aud-arq/mimicus-commercial-funnel-v1`
**Base:** `main@9a3da45d007892a5a027560e6dee36b9f87431ea`

## Problem

Setter discovery and LAYA triage can prioritize work, but the runtime cannot yet answer the operational question that matters most:

> Where does the commercial funnel lose prospects before a close?

Current state already distinguishes:
- prepared;
- contacted due/waiting;
- replied;
- qualified;
- proposal;
- won/lost.

Elevated commercial stages require matching evidence. What is missing is a deterministic, privacy-bounded analytical projection across those records.

## Goal

Build a read-only `CommercialFunnelService` that consumes:
- normalized `LeadCandidate` rows;
- the authoritative `LeadDecisionBatch`;
- explicit timezone-aware `as_of`.

It returns a canonical snapshot that can be used for operator review and future shadow-model calibration without changing LAYA decisions.

## Authority

- The funnel service never changes a `LeadDecision`.
- It performs no provider/model call.
- It performs no network call.
- It performs no setter-ledger mutation.
- It has no effect-dispatch capability.
- The authoritative decision remains `DeterministicLeadDecisionService`.

## Snapshot

Top-level fields:
- `as_of`;
- `policy_hash`;
- `batch_hash`;
- aggregate metrics for all leads;
- metrics by lane (`facebook`, `reddit`);
- sanitized calibration rows;
- `snapshot_hash`.

### Aggregate metrics

For each scope:
- lead count;
- disposition counts;
- next-action counts;
- current commercial-stage counts;
- terminal outcome counts (`won`, `lost`);
- terminal win rate = won / (won + lost), null when no terminal outcomes;
- `qualified_to_proposal` transition stats;
- `proposal_to_terminal` transition stats.

Transition stats:
- `eligible_count`: leads with evidence for the source stage;
- `advanced_count`: source + destination evidence in causal timestamp order;
- `rate`: advanced / eligible, null when denominator is zero;
- `median_hours`: median observed time between stages among advanced leads;
- `invalid_order_count`: leads whose destination evidence predates source evidence.

The service does not infer missing historical stages.

## Stage timestamps

For elevated stages, use the earliest matching `CommercialStageEvidence.observed_at <= as_of`.

- qualified timestamp: earliest qualified evidence;
- proposal timestamp: earliest proposal evidence;
- terminal timestamp: earliest won/lost evidence, paired with terminal outcome.

Future evidence is excluded from metrics.

## Calibration rows

One row per prospect, containing only:
- prospect_id;
- lane;
- setter_score;
- scam_risk;
- outreach_status;
- LAYA stage;
- commercial stage;
- disposition;
- next action;
- qualified_at;
- proposal_at;
- terminal_at;
- terminal_outcome.

Explicitly excluded:
- buyer;
- title;
- source/direct URL;
- evidence source_ref;
- evidence summary;
- free-text commercial note.

These rows are deterministic benchmark material, not training authority.

## Consistency checks

The service fails closed if:
- candidate IDs are duplicated;
- candidate ID set differs from `LeadDecisionBatch.input_ids`;
- a batch decision is missing for a candidate;
- `as_of` is naive;
- decision batch has duplicate prospect IDs.

## Non-goals

- predictive scoring;
- changing setter score;
- autonomous outreach;
- inferring replies from prose;
- estimating revenue;
- claiming causal conversion from incomplete historical evidence;
- sending calibration data to an external model.

## Next gate

A learned/shadow DecisionProvider can only be evaluated after enough terminal outcome rows exist. It may advise; it does not replace hard commercial policy without a separate benchmark and promotion decision.
