# Repository governance

## Purpose

MiMicus is developed by multiple human/AI operators in parallel. Governance exists to maximize parallel throughput without branch drift, duplicate authority, false PASS claims, or late merge collisions.

## Canonical truth

There are four distinct truths:

1. **Product truth** — `main`.
2. **Runtime truth** — the actually deployed version/SHA and its live observations.
3. **Task truth** — one task branch + its PR.
4. **Evidence truth** — exact-head test/run artifacts.

No branch, document, old CI run, simulation, or deployment may substitute for another truth class.

## Work contract

Every mutable task declares:

```text
ROLE=<ARQ|AUD|FIX|GOV>
BASE_SHA=<exact main SHA>
BRANCH=<name>
OBJECTIVE=<one bounded outcome>
OWNS=<paths + semantic contracts>
MUST_NOT_TOUCH=<paths/contracts>
ACCEPTANCE=<commands/gates/evidence>
INTEGRATION_OWNER=<one writer>
```

Path separation alone is not enough. Changes that share a schema, protocol, migration sequence, workflow, public API, authority boundary, or user-visible state are semantically coupled and must have one integration owner.

## Parallel execution

Safe parallel work:

- independent provider adapter vs independent cockpit styling;
- read-only audit vs implementation;
- tests for a stable interface vs unrelated documentation;
- research branches with no runtime authority.

Serialize:

- migrations;
- package/public API contracts;
- `MiMicusEngine` orchestration invariants;
- effect authorization;
- shared CI workflow;
- shared release/status documents;
- deployment configuration;
- any file/contract claimed by another active writer.

## Pull requests

All normal integration into `main` uses PRs.

PRs stay small enough to review and include:

- base/head SHAs;
- owned contract;
- changed paths;
- verification;
- evidence classification;
- runtime/deployment effect;
- unresolved findings.

A PR may be merged only after its affected gates are green on its current head and main-drift is reconciled.

Do not merge two competing implementations of the same contract. Choose one integration owner, verify, then retire the alternatives.

## Audit protocol

AUD is read-only unless explicitly promoted to FIX.

AUD records:

```text
AUDIT_BASE_SHA=<sha>
AUDIT_TARGET=<branch/PR/deployment>
FINDINGS=<severity + path/contract + evidence>
VERDICT=<PASS|PASS_WITH_FOLLOWUP|BLOCK>
```

If the target changes after audit, the verdict is historical until the changed surface is rechecked.

## Evidence and simulation

Operational evidence classification:

| Label | Meaning | Can satisfy live gate? |
| --- | --- | --- |
| VERIFIED_AT_HEAD | exact SHA reproduced | yes, for the proven local/CI gate |
| LIVE_OBSERVED | current live runtime observation | yes, for the specific observation |
| HISTORICAL | older SHA/run | no |
| UNVERIFIED | not reproduced | no |
| SIMULATED_FIXTURE | synthetic scenario/test data | no |
| UNKNOWN | insufficient evidence | no |

Simulation is first-class, not fake truth. Synthetic prospects, conversions, failures, agent activity, and market states may be generated to test behavior. They must carry `SIMULATED_FIXTURE` provenance end-to-end and UI surfaces must label them as simulation.

External simulators such as MiroFish may be evaluated behind an adapter. They never receive canonical memory/policy authority and their output never becomes live commercial evidence without a separate verification/promotion step.

## Status documents

`STATUS.md` is a checkpoint, not a timeless claim. Release claims should include the exact verified SHA and CI/run reference whenever possible.

Do not update `STATUS.md` from an unmerged feature branch unless the text explicitly describes that branch.

## Branch lifecycle

Branch categories:

- **canonical**: `main`;
- **active integration**: branches with an open/active task or PR;
- **release reference**: release branches aligned intentionally to a verified checkpoint;
- **historical/provenance**: legacy, old ORDER, merged architecture checkpoints;
- **experiment/proposal**: never canonical.

After merge, source branches are candidates for deletion once their commit/PR provenance is durable. Branch deletion is a housekeeping action and requires owner authorization; history must never be force-erased merely to make the branch list smaller.

## Repository evidence

- `core/evidence/`: historical ORDER evidence; treat as provenance unless regenerated for current HEAD.
- root `evidence/`: current combined-repository deployment/integration evidence only.
- generated logs/build output do not belong in git unless explicitly required as durable evidence.
- large repeatable artifacts should be regenerated, not copied between task branches.

## Release/deployment

Repository readiness, release readiness, and deployment readiness are separate gates.

A green CI run does not imply the public Worker is running that SHA. A live site response does not imply the Python core was deployed. Every release report must state both repository SHA and deployed identity.

Production deployment remains an explicit owner decision.
