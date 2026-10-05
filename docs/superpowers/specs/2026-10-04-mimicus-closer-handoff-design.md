# MiMicus Closer Handoff V1 — Design

**Date:** 2026-10-04  
**Branch:** `aud-arq/mimicus-closer-handoff-v1`  
**Base:** `main@30b5d7b36c7387315e92bc64b7d0febaa63d4d4b`

## Problem

LAYA already decides which commercial leads are `WORK_NOW` and emits a deterministic `next_action` such as `QUALIFY`, `PROPOSE` or `FOLLOW_UP`.

The current batch still hands downstream consumers mostly IDs. That leaves an operational gap between decision and closer work.

## Goal

Create a deterministic, audit-friendly closer handoff for every `WORK_NOW` decision without enabling any external side effect.

## CommercialActionTicket

Frozen fields:

- `prospect_id`
- `lane`
- `buyer`
- `title`
- `source_url`
- `direct_url`
- `commercial_stage`
- `next_action`
- `rank_position`
- `decision_hash`
- `effect_scope = commercial-outreach`
- `requires_human_approval = true`
- `ticket_hash`

`ticket_hash` is SHA-256 over the semantic ticket fields excluding itself.

## Authority

- only LAYA / `DeterministicLeadDecisionService` creates tickets;
- only decisions with `disposition=WORK_NOW` receive tickets;
- the ticket is **not** an `EffectApprovalReceipt`;
- a closer/advisor may consume the ticket to prepare work, but an actual message/send remains blocked by the existing effect authorization boundary;
- HOLD / REPAIR_DATA / REJECT / COMPLETE never produce action tickets.

## Batch contract

`LeadDecisionBatch` gains canonical `action_queue`.

The queue is sorted by lane, rank position and prospect ID and is bound into `batch_hash`.

`selected_by_lane` remains for compatibility.

## UI

`decision_emitted` already exposes `next_action`; the cockpit should display it. No decision logic moves into JavaScript.

## Non-goals

- automatic message drafting;
- LLM closer agent;
- automatic send;
- CRM mutation;
- browser automation;
- effect approval issuance;
- changing rank policy.
