# Branch map

## Current release

- `release/mimicus-v0.3-prep` — **current verified release candidate**.
- `main` — legacy default branch until the controlled default-main transition.

Exact-head release verification at `1f9171accebb5bdd763bb9203b9f3fff0b53611b` passed core tests/coverage, Ruff, mypy, package build, cockpit syntax and Wrangler dry-run.

## Preserved legacy default

- `legacy/main-setters-radar-2026-10-03` — immutable preservation point for the previous default `main` before product consolidation.

No history is being discarded during the default-branch transition.

## Architecture checkpoints

Retained for audit/provenance:

- `aud-arq/mimicus-lead-decision-v1`
- `aud-arq/mimicus-live-observer-v1`
- `aud-arq/mimicus-scheduler-v1`
- `aud-arq/mimicus-effects-v1`
- `aud-arq/mimicus-causal-replay-v1`
- `aud-arq/mimicus-capability-review-v1`

The release candidate descends from the causal-replay checkpoint and contains the preceding runtime work.

## Historical product branches

- `mimicus-iaffice-v1`
- `mimicus-v2-monochrome`

These remain for provenance and comparison.

## Independent architecture proposals

- `grokbot/mimicus-zero-cost-architecture`
- `sonnet55/mimicus-zero-cost-architecture`

These remain proposal/evidence branches only and have no production authority.

## Older ORDER branches

The `order-*` branches predate this formal release consolidation and are not current release sources.
