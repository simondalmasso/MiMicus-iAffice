# MiMicus iAffice — Current checkpoint

**State now:** repository consolidation is complete and `main` is the canonical product branch.  
**Release staging branch:** `release/mimicus-v0.3-prep` mirrors the same product line.  
**Legacy default-main preservation:** `legacy/main-setters-radar-2026-10-03`.

## Verified release gates

The consolidated product has passed:

- **200 tests PASS**
- **90.24% total coverage** (required: 90%)
- **Ruff PASS**
- **mypy PASS**
- **Python package build PASS**
- **cockpit JavaScript syntax PASS**
- **Cloudflare Worker dry-run PASS** with Wrangler 4.134.0

The CI workflow runs these gates on `main` and the release staging branch.

## Architecture implemented now

- active Python runtime under `core/`;
- LAYA / `MiMicusEngine` remains the single orchestration authority;
- deterministic commercial lead decision gate;
- live read-only LAYA observer;
- completion-driven DAG scheduler;
- one-use exact-envelope effect authorization;
- causal replay anchored to the append-only event ledger;
- observational Cloudflare cockpit;
- no autonomous real-world effect adapter enabled.

## Repository state now

- old `archive/` presentation removed;
- one-time source-absorption workflow retired;
- nested legacy workflow metadata removed from `core/`;
- consolidated `Mimicus CI` covers core + cockpit gates;
- root/core documentation synchronized;
- historical deployment evidence explicitly marked historical;
- external capability research lives under `docs/research/` and has no runtime authority.

## Safety state now

- effects are deny-by-default;
- approval is exact, durable, time-bounded and one-use;
- uncertain remote effect outcomes do not blind-retry;
- external frameworks do not gain orchestration authority;
- public Worker does not provide command ingress into LAYA.

## Deployment status now

**Current code is not being deployed yet.**

Repository/release readiness is ahead of deployment readiness.

Remaining deployment work:

1. exact-head CI on canonical `main`;
2. optional preview/live health verification;
3. production deployment only after explicit release decision.

There is no known architectural blocker at this checkpoint.
