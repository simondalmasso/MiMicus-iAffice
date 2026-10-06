# MiMicus iAffice — Current checkpoint

**Canonical branch:** `main`  
**Verified canonical checkpoint:** `128ec20e274d1df1342fdb13197a3011feb25067`  
**Exact-main verification:** Mimicus CI run `37432414824` — PASS  
**Release staging branch:** `release/mimicus-v0.3-prep` remains a historical release reference until explicitly synchronized and reverified.  
**Legacy default-main preservation:** `legacy/main-setters-radar-2026-10-03`.

## Verified release gates

The exact canonical checkpoint passed:

- locked Python install from `core/requirements.lock` + editable `--no-deps` install + `pip check`;
- **290 tests PASS**;
- **90.47% total coverage** (required: 90%);
- **Ruff PASS**;
- **mypy PASS** across 109 source files;
- Python sdist + wheel build PASS;
- commercial triage smoke PASS;
- commercial funnel smoke PASS;
- cockpit JavaScript syntax PASS;
- cockpit DOM/provenance contract PASS;
- Cloudflare Worker dry-run PASS.

## Architecture implemented now

- active Python runtime under `core/`;
- LAYA / `MiMicusEngine` remains the single orchestration authority;
- deterministic commercial lead decision gate;
- canonical `CommercialActionTicket` queue for `WORK_NOW` leads;
- deterministic `CommercialActionGoal` success criteria derived by LAYA, hash-bound and never treated as permission to act;
- read-only commercial funnel analytics with sanitized calibration rows and stage-transition metrics;
- deterministic zero-cost `CommercialFunnelDiagnosis` with explicit hash-bound policy;
- partial downstream/terminal samples fail closed to `INSUFFICIENT_DATA`;
- deterministic read-only `CommercialInterventionPlan` derived from the diagnosis + exact diagnosis policy, with measurable hash-bound criteria and no send/CRM/ranking/effect authority;
- `mimicus funnel --diagnose --intervene` exposes that analytical intervention contract without changing default funnel output;
- live read-only LAYA observer;
- completion-driven DAG scheduler;
- source-controlled action admission: only exact `READ_ONLY` classifications may bypass the effect gate; `MUTATING` and unknown fail closed;
- one-use exact-envelope effect authorization and separate `EffectDispatcher` authority;
- causal replay anchored to the append-only event ledger;
- optional NVIDIA NIM / DeepSeek V4.1 Flash provider profile with explicit credential/cost guardrails and an application-level output-token ceiling;
- MCP Python SDK pinned to patched `2.2.0`;
- MCP Streamable HTTP mutating surface restricted to loopback until transport authentication exists;
- observational Cloudflare cockpit with public synthetic data explicitly classified as `SIMULATED_FIXTURE`;
- cockpit DOM/provenance CI prevents missing DOM references and archived checkpoint SHAs from being mislabeled as current source truth;
- hardened Worker response headers and explicit JSON 404 for unknown `/api/*` routes in repository code;
- no autonomous real-world effect adapter enabled.

## Repository state now

- `main` is the only canonical product branch;
- no open pull requests or issues remained immediately after integrating PRs #31 and #32;
- consolidated `Mimicus CI` covers core + cockpit gates;
- `core/requirements.lock` is enforced by CI;
- a guarded manual production workflow now exists at `.github/workflows/deploy-production.yml`;
- production deployment requires `main`, explicit `DEPLOY_MIMICUS` confirmation, an exact approved SHA, a successful exact-head main CI run, the GitHub `production` environment, Cloudflare credentials, predeploy cockpit gates and postdeploy live acceptance;
- divergent branches were audited on 2026-10-06 and classified in `docs/BRANCH-AUDIT-2026-10-06.md`; no divergent branch is a missing canonical runtime blocker;
- branch deletion remains a separate owner-authorized hygiene action;
- the USD 0 operating boundary is documented in `docs/OPERATING-COST.md`;
- historical deployment evidence and archived core SHA `565407e...` remain explicitly historical;
- external capability research under `docs/research/` has no runtime authority.

## USD 0 state

The **mandatory baseline has USD 0 mandatory monetary spend** under the documented conditions:

- default/offline Python profile;
- SQLite/local persistence;
- deterministic/scripted provider path;
- local loopback MCP;
- commercial deterministic analytics;
- public cockpit while Cloudflare remains within applicable Free-plan limits;
- standard GitHub-hosted CI while this repository remains public.

This is not a claim that every optional provider or unlimited production usage is free. NVIDIA NIM remains optional and fail-closed as `known_zero_cost=false` unless the operator has verified current entitlement for the exact development/prototyping session. OpenAI is optional and is not part of the mandatory USD 0 baseline. Unknown cost evidence remains `UNKNOWN`, not `USD 0 VERIFIED`.

## Safety state now

- effects are deny-by-default;
- only exact source-controlled `READ_ONLY` action classifications may bypass the effect boundary;
- effect approval is exact, durable, time-bounded and one-use;
- uncertain remote effect outcomes do not blind-retry;
- commercial action goals, funnel diagnoses and intervention plans describe/measure state but do not grant send, CRM, ranking, stage or effect authority;
- external frameworks do not gain orchestration authority;
- public Worker does not provide command ingress into LAYA.

## Deployment status now

**Repository code is still ahead of the public Cloudflare deployment. Production is not verified at the canonical checkpoint.**

Fresh public probe on **2026-10-06 ~07:40 UTC** confirmed `PROD_DRIFT`:

- `/health` returned cached HTML with HTTP 200 rather than the repository JSON health response;
- unknown `/api/definitely-not-real` returned HTML with HTTP 200 rather than the repository JSON 404 contract;
- `/` and `/health` lacked the repository security-header set;
- `/api/health` and `/api/runtime` exposed only part of the expected security-header set.

The previous “missing deploy channel” blocker is resolved in repository code by PR #32. The deployment itself was **not** run because production release/deploy requires an explicit owner decision and valid Cloudflare credentials.

Remaining operational work:

1. explicitly authorize the exact canonical SHA for production;
2. ensure the GitHub `production` environment has `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`;
3. manually dispatch `Mimicus production deploy` with `DEPLOY_MIMICUS` and the exact approved SHA;
4. require the workflow live-acceptance gate to verify security headers, JSON health/runtime and JSON 404 behavior;
5. only then mark production `VERIFIED`.

There is no known repository architecture blocker at this checkpoint. The only unresolved release state is operational **PROD_DRIFT / explicit production release not yet executed**.
