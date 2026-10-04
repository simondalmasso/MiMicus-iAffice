# MiMicus Commercial Stage Evidence V1 — Design

**Date:** 2026-10-04  
**Branch:** `aud-arq/mimicus-commercial-evidence-v1`  
**Base:** `main@370c1e3fc2fc9e8d9f81ccbf1f2bc8e3b49efad9`

## Problem

The current commercial progression model accepts `commercial.stage=qualified|proposal|won|lost` as authoritative input. Because those stages outrank ordinary setter status, an upstream row can manufacture priority without structured evidence.

## Goal

Keep the commercial path deterministic and $0 while making elevated stages auditable.

## Evidence model

Add frozen `CommercialStageEvidence`:

- `stage`: commercial stage being evidenced;
- `observed_at`: timezone-aware timestamp;
- `source_ref`: non-empty opaque reference/URL/thread locator;
- `summary`: optional short operator note.

`CommercialContext` gains `evidence: tuple[CommercialStageEvidence, ...]`.

## Authority rule

Stages requiring matching evidence:

- `qualified`
- `proposal`
- `won`
- `lost`

For those stages, LAYA requires at least one evidence item whose `stage` exactly matches the asserted commercial stage.

Evidence observed after explicit decision `as_of` is invalid for that decision.

If the stage is elevated but evidence is missing/mismatched/future-dated, disposition is `REPAIR_DATA`; it does not receive stage priority.

`unknown` and `discovery` remain backward compatible.

## Non-goals

- model-based qualification;
- CRM integration;
- automatic stage inference from prose;
- scoring buyer intent with an LLM;
- autonomous outreach;
- changing setter authority beyond requiring evidence for stage escalation.

## Security / replay

Commercial evidence is part of `LeadCandidate`, therefore already bound by candidate input hash, decision hash and batch hash.
