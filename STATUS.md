# MiMicus iAffice — Current checkpoint

**Canonical branch:** `main`  
**Verified runtime checkpoint:** `8996aafa5d394c1d90ba48e45dce8175b7f60fd5`  
**Exact-main CI:** `37400894504` — PASS  
**Release staging branch:** `release/mimicus-v0.3-prep` is a historical release reference and trails canonical `main` until explicitly synchronized and reverified.  
**Legacy default-main preservation:** `legacy/main-setters-radar-2026-10-03`.

## Verified release gates

The exact canonical runtime checkpoint passed:

- locked Python install from `core/requirements.lock` + editable `--no-deps` install + `pip check`;
- **269 tests PASS**;
- **90.29% total coverage** (required: 90%);
- **Ruff PASS**;
- **mypy PASS** across 107 source files;
- Python sdist + wheel build PASS;
- cockpit JavaScript syntax PASS;
- cockpit DOM/provenance contract PASS;
- Cloudflare Worker dry-run PASS.

`Mimicus CI` is therefore verifying the checked-in dependency lock instead of resolving floating transitive dependencies during the gate.

## Architecture implemented now

- active Python runtime under `core/`;
- LAYA / `MiMicusEngine` remains the single orchestration authority;
- deterministic commercial lead decision gate;
- canonical `CommercialActionTicket` queue for `WORK_NOW` leads;
- deterministic `CommercialActionGoal` success criteria derived by LAYA, bound into ticket/batch hashes and never treated as permission to act;
- read-only commercial funnel analytics with sanitized calibration rows and stage-transition metrics;
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
- no open pull requests remain at this checkpoint;
- old `archive/` presentation removed;
- one-time source-absorption workflow retired;
- nested legacy workflow metadata removed from `core/`;
- consolidated `Mimicus CI` covers core + cockpit gates;
- `core/requirements.lock` is enforced by CI;
- root/core governance and security documentation are synchronized to the current runtime surface;
- commercial source/setter authority and measurable action-goal contracts are documented in `docs/COMMERCIAL-DATA-CONTRACT.md`;
- historical deployment evidence and archived core SHA `565407e...` are explicitly labeled historical;
- external capability research under `docs/research/` has no runtime authority.

## Safety state now

- effects are deny-by-default;
- only exact source-controlled `READ_ONLY` action classifications may bypass the effect boundary;
- effect approval is exact, durable, time-bounded and one-use;
- uncertain remote effect outcomes do not blind-retry;
- commercial goals describe success criteria but do not grant send, CRM, stage or effect authority;
- external frameworks do not gain orchestration authority;
- public Worker does not provide command ingress into LAYA.

## Deployment status now

**Repository code is ahead of the public Cloudflare deployment. Production is not verified at the canonical checkpoint.**

Fresh public probe on **2026-10-05 ~22:50 ART / 2026-10-06 ~01:50 UTC** confirms `PROD_DRIFT`:

- `/health` returns cached HTML with HTTP 200 rather than the repository Worker JSON health response;
- an unknown route such as `/api/definitely-not-real` returns HTML with HTTP 200 rather than the repository JSON 404 contract;
- the live responses do not expose the full security-header set implemented in repository code;
- therefore the public Worker is serving an older bundle than canonical `main`.

No production deploy workflow or authorized Cloudflare Workers credential channel is present in this repository, so this audit did **not** perform a deployment.

Remaining operational work:

1. deploy the exact verified canonical checkpoint through an authorized Cloudflare Workers channel;
2. re-probe `/`, `/health`, `/api/health`, `/api/runtime` and an unknown `/api/*` route;
3. require the repository security headers, JSON 404 behavior and truthful historical-checkpoint labeling to match live;
4. only then mark production verified or make a release decision.

There is no known repository architecture blocker at this checkpoint. The outstanding blocker is operational **PROD_DRIFT / missing authorized deploy channel**.
