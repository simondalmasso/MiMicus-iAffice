# Mimicus Commercial Conversion Gate V1

**Branch:** `aud-arq/mimicus-conversion-gate-v1`
**Base:** `main@a4845a829827d7a9d2b653a1ee37ede164868077`

## Problem

The current deterministic lead gate prioritizes operational outreach state but cannot represent commercial progression after a reply.

It cannot distinguish:
- replied but still unqualified;
- qualified opportunity;
- proposal sent;
- won;
- lost.

As a result LAYA can order follow-up work but cannot optimize the queue toward closure.

## V1 scope

Add one optional structured `commercial` block to prospect input:

```json
{
  "stage": "unknown | discovery | qualified | proposal | won | lost",
  "updatedAt": "ISO-8601 | null",
  "note": "string | null"
}
```

Absence of the block preserves current behavior.

No free-text inference is performed.

## Decision semantics

Priority:
`proposal > qualified > replied > prepared > contacted_due > contacted_waiting`.

Terminal:
- `won` -> `COMPLETE`
- `lost` -> `COMPLETE`

Legacy `outreach.status=closed` without explicit commercial outcome keeps existing REJECT behavior.

Next action:
- proposal -> FOLLOW_UP
- qualified -> PROPOSE
- replied -> QUALIFY
- prepared -> CONTACT
- contacted_due -> FOLLOW_UP
- contacted_waiting -> WAIT
- terminal -> NONE

Hard policy rejects (scam, fee, ineligible) remain authoritative.

## Non-goals

- predictive conversion model;
- LLM inference from notes;
- automatic outreach;
- pricing/proposal generation;
- changing effect authorization;
- changing setter source ownership.

## Compatibility

V1 ledger rows without `commercial` remain valid and rank exactly as before.
