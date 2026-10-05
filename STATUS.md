# MiMicus iAffice — Current checkpoint

**State now:** repository consolidation is complete and `main` is the canonical product branch.  
**Release staging branch:** `release/mimicus-v0.3-prep` is being aligned to the canonical `main` checkpoint.  
**Legacy default-main preservation:** `legacy/main-setters-radar-2026-10-03`.

## Verified release gates

Canonical checkpoint: `main@99630429edcbf2cff9a397b97e8b60ecbdde91b4`  
Post-merge CI: `37272050139` — **SUCCESS**


The consolidated product has passed:

- **243 tests PASS**
- **90.27% total coverage** (required: 90%)
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
- commercial closer handoff with canonical `CommercialActionTicket` queue for `WORK_NOW` leads;
- read-only commercial funnel analytics with sanitized calibration rows and stage-transition metrics;
- live read-only LAYA observer;
- completion-driven DAG scheduler;
- one-use exact-envelope effect authorization;
- causal replay anchored to the append-only event ledger;
- optional NVIDIA NIM / DeepSeek V4.1 Flash provider profile behind explicit credential/cost configuration;
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

Repository/release readiness is ahead of deployment readiness. Commercial closure PR #11 is merged into `main`; post-merge CI run `37272050139` is SUCCESS. No deployment has been triggered.

Remaining deployment work:

1. optional preview/live health verification;
2. production deployment only after explicit release decision.

There is no known architectural blocker at this checkpoint.
