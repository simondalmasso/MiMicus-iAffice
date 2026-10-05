# MiMicus iAffice — Agent operating contract

This file is the entry contract for every coding/review agent working in this repository.

## Authority

- `main` is the only canonical product branch.
- LAYA / `MiMicusEngine` remains the single runtime orchestration authority.
- An agent may inspect any branch, but may write only inside its declared task branch and owned semantic area.
- Do not deploy production, enable real-world effects, delete branches, rewrite history, or weaken safety gates without explicit owner authorization.

## Required startup

Before changing code:

1. read `STATUS.md`, `docs/ARCHITECTURE.md`, `docs/GOVERNANCE.md`, and `docs/REPOSITORY.md`;
2. record `BASE_SHA=<exact main SHA>`;
3. create/use one task branch;
4. declare role, objective, owned paths/contracts, forbidden scope, and verification;
5. check current open PRs/active branches for overlap.

## Multi-agent rule

One writer owns one semantic contract at a time.

Two agents may inspect the same code read-only. They must not concurrently mutate the same contract, schema, workflow, migration chain, public API, or integration file even when filenames differ.

Roles:

- `ARQ`: implementation/architecture writer.
- `AUD`: independent reviewer; read-only by default.
- `FIX`: bounded corrective writer for verified findings.
- `GOV`: repository/governance changes only.

AUD never pushes fixes onto an ARQ branch. Verified fixes use a separate `fix/` branch or are handed to the current integration owner.

## Branch names

Use:

- `arq/<area>-<task>-vN`
- `aud/<area>-<task>-vN`
- `fix/<area>-<finding>-vN`
- `governance/<task>-vN`
- `exp/<topic>-vN` for disposable experiments

`legacy/`, `archive/`, old `order-*`, proposal branches, and historical product branches are not integration sources unless explicitly reactivated.

## No direct-main development

Normal development lands through a PR. A PR must identify:

- exact `BASE_SHA`;
- current `HEAD_SHA`;
- owned semantic area;
- changed paths;
- gates run;
- evidence class;
- unresolved risks.

If `main` moves while work is in progress, do not silently assume the old audit still applies. Recheck drift before merge.

## Truth labels

Every material operational claim uses one of these labels:

- `VERIFIED_AT_HEAD`: reproduced on the exact claimed SHA.
- `LIVE_OBSERVED`: observed from the current deployed/runtime surface.
- `HISTORICAL`: valid evidence for an older SHA/run only.
- `UNVERIFIED`: plausible or implemented but not currently proven.
- `SIMULATED_FIXTURE`: synthetic/test data; never presented as real business/runtime evidence.
- `UNKNOWN`: insufficient evidence.

Synthetic or MiroFish-style simulation is allowed for tests, scenario generation, stress cases, and UI development, but it cannot satisfy a live-production gate. The cockpit must visually distinguish simulation from live telemetry.

## Completion

Do not call a task DONE because code exists.

Before a completion claim:

1. verify exact final HEAD;
2. run the task's focused tests;
3. run all affected integration/release gates;
4. ensure no later code commit invalidated evidence;
5. report unresolved items explicitly.

See `docs/GOVERNANCE.md` for the full integration protocol.
