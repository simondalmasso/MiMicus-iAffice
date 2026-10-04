# MiMicus iAffice — Current checkpoint

**State now:** repository consolidation and release audit are in progress.  
**Release branch:** `release/mimicus-v0.3-prep`  
**Validated architecture baseline:** `aud-arq/mimicus-causal-replay-v1@57c37aad32866b409b0b9c6fad6f70799c90760e`

## Verified at the last architecture checkpoint

- **200 tests PASS**
- **90.24% total coverage** (required: 90%)
- **Ruff PASS**
- **mypy PASS** across 104 source files
- **package build PASS**
- commercial lead decision gate implemented
- live read-only LAYA observer implemented
- completion-driven DAG scheduler implemented
- one-use exact-envelope effect authorization implemented
- causal replay anchored to the append-only event ledger
- Worker/cockpit remains observational

## Repository state now

- active Python runtime is promoted to `core/`;
- historical `archive/` naming is removed from the release branch;
- one-time source-absorption workflow is retired;
- branch-specific TDD workflow is replaced by `Mimicus Core CI`;
- root project documentation is being normalized for formal review;
- default `main` remains untouched until this release branch passes the post-move gates.

## Safety state now

- no autonomous browser, messaging, payment, shell or other real-world effect adapter is enabled;
- effects are deny-by-default and require an exact durable one-use approval;
- unknown remote effect outcomes do not blind-retry;
- external frameworks do not receive orchestration authority;
- the public Worker is not an execution bridge into LAYA.

## Deployment status now

**Not deploying yet.**

Remaining gates:

1. post-restructure full CI from `core/`;
2. Worker dry-run and cockpit syntax;
3. local observer smoke against a representative prospect fixture;
4. final branch diff + security review;
5. only then decide whether to make this structure the default branch and whether to deploy.

No architectural blocker is currently known.
