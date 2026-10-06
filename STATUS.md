# MiMicus iAffice — Current checkpoint

**Canonical branch:** `main`  
**Verified runtime checkpoint:** `50eea9daa760bf03b432ea0679b4e877c561611a`  
**Runtime-tree verification:** PR #28 exact head `19ef7d677b8f8d237952aa2c1c9d18a56cfeb320`, CI `37402263411` — PASS with zero base drift immediately before merge  
**Release staging branch:** `release/mimicus-v0.3-prep` remains a historical release reference until explicitly synchronized and reverified.  
**Legacy default-main preservation:** `legacy/main-setters-radar-2026-10-03`.

## Verified release gates

The canonical runtime tree has passed:

- locked Python install from `core/requirements.lock` + editable `--no-deps` install + `pip check`;
- **279 tests PASS**;
- **90.38% total coverage** (required: 90%);
- **Ruff PASS**;
- **mypy PASS** across 108 source files;
- Python sdist + wheel build PASS;
- cockpit JavaScript syntax PASS;
- cockpit DOM/provenance contract PASS;
- Cloudflare Worker dry-run PASS.

## Architecture implemented now

- active Python runtime under `core/`;
- LAYA / `MiMicusEngine` remains the single orchestration authority;
- deterministic commercial lead decision gate;
- canonical `CommercialActionTicket` queue for `WORK_NOW` leads;
- deterministic `CommercialActionGoal` success criteria derived by LAYA, bound into ticket/batch hashes and never treated as permission to act;
- read-only commercial funnel analytics with sanitized calibration rows and stage-transition metrics;
- deterministic zero-cost `CommercialFunnelDiagnosis` over sanitized funnel snapshots;
- funnel diagnosis policy is explicit and hash-bound; no model/provider, ranking mutation, setter mutation, effect approval or send is introduced;
- diagnosis fails closed to `INSUFFICIENT_DATA` when downstream/terminal sample evidence is partial; `NO_OBSERVED_BOTTLENECK` requires configured minimum sample counts across qualified→proposal, proposal→terminal and terminal outcomes;
- optional `mimicus funnel --diagnose` leaves default funnel output unchanged;
- live read-only LAYA observer;
- completion-driven DAG scheduler;
- source-controlled action admission: exact `READ_ONLY` operations are the only actions allowed to bypass the effect gate; `MUTATING` and unknown actions fail closed;
- one-use exact-envelope effect authorization and separate `EffectDispatcher` authority;
- causal replay anchored to the append-only event ledger;
- optional NVIDIA NIM / DeepSeek V4.1 Flash provider profile with explicit credential/cost guardrails and an application-level output-token ceiling;
- MCP Python SDK pinned to patched `2.2.0`;
- MCP Streamable HTTP mutating surface restricted to loopback until transport authentication exists;
- observational Cloudflare cockpit with public synthetic data explicitly classified as `SIMULATED_FIXTURE`;
- cockpit DOM/provenance CI prevents JavaScript references to missing DOM IDs and prevents archived checkpoint SHAs from being labeled as current source truth;
- hardened Worker response headers and explicit JSON 404 for unknown `/api/*` routes in repository code;
- no autonomous real-world effect adapter enabled.

## Repository state now

- `main` is the only canonical product branch;
- no open pull requests remained immediately before this status-only checkpoint PR;
- old `archive/` presentation removed;
- one-time source-absorption workflow retired;
- nested legacy workflow metadata removed from `core/`;
- consolidated `Mimicus CI` covers core + cockpit gates;
- `core/requirements.lock` is enforced by CI;
- root/core governance and security documentation are synchronized to the current runtime surface;
- commercial source/setter authority, measurable action-goal and read-only funnel-diagnosis contracts are documented in `docs/COMMERCIAL-DATA-CONTRACT.md`;
- historical deployment evidence and archived core SHA `565407e...` are explicitly labeled historical;
- external capability research under `docs/research/` has no runtime authority.

## Safety state now

- effects are deny-by-default;
- only exact source-controlled `READ_ONLY` action classifications may bypass the effect boundary;
- effect approval is exact, durable, time-bounded and one-use;
- uncertain remote effect outcomes do not blind-retry;
- commercial action goals and funnel diagnoses describe/measure state but do not grant send, CRM, ranking, stage or effect authority;
- partial funnel evidence cannot manufacture a healthy/no-bottleneck diagnosis;
- external frameworks do not gain orchestration authority;
- public Worker does not provide command ingress into LAYA.

## Deployment status now

**Repository code is ahead of the public Cloudflare deployment. Production is not verified at the canonical checkpoint.**

Fresh public probe on **2026-10-05 ~23:06 ART / 2026-10-06 ~02:06 UTC** confirms `PROD_DRIFT`:

- `/health` returns cached HTML with HTTP 200 rather than the repository Worker JSON health response;
- an unknown route such as `/api/definitely-not-real` returns HTML with HTTP 200 rather than the repository JSON 404 contract;
- `/` and `/health` lack the repository security-header set;
- `/api/health` and `/api/runtime` expose only part of the expected security-header set;
- therefore the public Worker is serving an older bundle than canonical `main`.

No production deploy workflow or authorized Cloudflare Workers credential channel is present in this repository, so this audit did **not** perform a deployment.

Remaining operational work:

1. deploy the exact verified canonical checkpoint through an authorized Cloudflare Workers channel;
2. re-probe `/`, `/health`, `/api/health`, `/api/runtime` and an unknown `/api/*` route;
3. require repository security headers, JSON 404 behavior and truthful historical-checkpoint labeling to match live;
4. only then mark production verified or make a release decision.

There is no known repository architecture blocker at this checkpoint. The outstanding blocker is operational **PROD_DRIFT / missing authorized deploy channel**.
