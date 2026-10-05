# Branch governance

The live GitHub branch list is authoritative. This document defines branch classes rather than attempting to maintain a permanently complete branch inventory.

## Canonical

- `main` — the only canonical MiMicus iAffice product branch.

## Active work

New work uses role-specific names:

- `arq/<area>-<task>-vN` — implementation/architecture;
- `aud/<area>-<task>-vN` — read-only audit state when a branch is useful;
- `fix/<area>-<finding>-vN` — bounded correction;
- `governance/<task>-vN` — repository governance only;
- `exp/<topic>-vN` — disposable experiments/proposals.

Every active writer records an exact base SHA and opens a PR before integration.

## Release reference

- `release/mimicus-v0.3-prep` — release reference/staging line.

A release branch must not be described as aligned with `main` unless its SHA/ancestry was checked at the time of the claim.

## Historical / provenance

Existing branches under these families are retained only for provenance unless explicitly reactivated:

- `legacy/*`;
- old `order-*`;
- old `aud-arq/*` architecture checkpoints;
- historical `mimicus-*` product branches;
- `grokbot/*` and `sonnet55/*` architecture proposals.

A historical branch has no production or integration authority merely because it still exists.

## Merged source branches

Merged implementation branches may be retained temporarily for audit provenance, then deleted as housekeeping after owner authorization. Do not keep merged branches indefinitely just to preserve history: the merge commit/PR is the durable provenance.

## Collision rule

Different filenames do not guarantee independence. If two branches alter the same schema, migration chain, workflow, public API, authority boundary, orchestration invariant, deployment config, or release-status truth, they are coupled and require one integration owner.

See `AGENTS.md` and `docs/GOVERNANCE.md`.
