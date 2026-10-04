# Branch map

This repository preserves historical development branches, but only one branch is the current release candidate.

## Current

- `release/mimicus-v0.3-prep` — **current release candidate**. Formal repository layout, active `core/`, cockpit, consolidated architecture and release documentation.
- `main` — **legacy default branch until release audit completes**. It contains older setter/radar material and is intentionally not the current product source of truth.

## Architecture checkpoints

These branches are retained as immutable/auditable checkpoints of the Mimicus architecture work:

- `aud-arq/mimicus-lead-decision-v1`
- `aud-arq/mimicus-live-observer-v1`
- `aud-arq/mimicus-scheduler-v1`
- `aud-arq/mimicus-effects-v1`
- `aud-arq/mimicus-causal-replay-v1`
- `aud-arq/mimicus-capability-review-v1`

The release candidate already descends from the causal-replay checkpoint and includes the preceding runtime work.

## Historical product branches

- `mimicus-iaffice-v1`
- `mimicus-v2-monochrome`

These remain for provenance and comparison. They are not active release branches.

## Independent architecture proposals

- `grokbot/mimicus-zero-cost-architecture`
- `sonnet55/mimicus-zero-cost-architecture`

These are evidence/proposal branches only. They do not have production authority.

## Legacy non-release work

The `order-*` branches predate the formal Mimicus release consolidation and are not part of the current release candidate.

## Default-branch transition

The old `main` will be preserved under a clearly named legacy branch before any default-branch replacement. The release candidate must pass post-restructure CI and final review first.
