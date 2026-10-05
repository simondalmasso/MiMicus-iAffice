# Branch map

## Canonical

- `main` — **canonical MiMicus iAffice product branch**.
- `release/mimicus-v0.3-prep` — release staging/reference branch; maintained aligned to the current canonical product checkpoint after verification.

## Preserved legacy default

- `legacy/main-setters-radar-2026-10-03` — preservation point for the previous default `main` before product consolidation.

No history was discarded during the transition.

## Active integration provenance

- `arq/mimicus-commercial-closure-v1` — source branch for merged PR #11 (commercial funnel + closer handoff); retained for audit provenance.

## Architecture checkpoints

Retained for audit/provenance:

- `aud-arq/mimicus-lead-decision-v1`
- `aud-arq/mimicus-live-observer-v1`
- `aud-arq/mimicus-scheduler-v1`
- `aud-arq/mimicus-effects-v1`
- `aud-arq/mimicus-causal-replay-v1`
- `aud-arq/mimicus-capability-review-v1`

The canonical branch descends from the causal-replay checkpoint and contains the preceding runtime work.

## Historical product branches

- `mimicus-iaffice-v1`
- `mimicus-v2-monochrome`

These remain for provenance and comparison.

## Independent architecture proposals

- `grokbot/mimicus-zero-cost-architecture`
- `sonnet55/mimicus-zero-cost-architecture`

These are proposal/evidence branches only and have no production authority.

## Older ORDER branches

The `order-*` branches predate the formal release consolidation and are not current release sources.
