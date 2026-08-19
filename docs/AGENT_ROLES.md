# Agent roles

- CEO: chooses one current priority and assignments from verified deltas; protected external authority remains gated.
- Research: creates sourced claims from authorized/public data.
- CMO: drafts content only from verified/promoted evidence; no auto-publish.
- Sales: scores lead intent/staleness deterministically and drafts follow-up; no auto-send.
- Data: calculates funnel metrics/anomalies deterministically before interpretation.
- Dev: diagnoses incidents and proposes isolated changes; no merge/deploy/secret mutation.
- AUD: independently checks provenance/freshness/calculation/policy and emits PASS/FAIL/UNCERTAIN using a different deterministic challenge path for the reference material claim.

`TaskRouter` stores the minimal coalition, model tier, deterministic-first flag and selection reason.
