# Operating cost contract

Checked: **2026-10-06**

MiMicus is designed so its mandatory baseline can operate with **USD 0 mandatory monetary spend**. That statement has strict boundaries and does not mean every optional provider or every production-scale usage pattern is free.

## USD 0 mandatory baseline

The current baseline is:

- Python core on the `offline` profile;
- local SQLite persistence;
- deterministic/scripted provider path;
- commercial triage, action-goal and funnel-diagnosis logic;
- local MCP on loopback;
- repository tests, replay and evidence tooling;
- Cloudflare cockpit using only the Worker + static-assets surface currently declared in `wrangler.toml`;
- GitHub Actions on standard GitHub-hosted runners while this repository remains public.

The default profile is `offline`. No OpenAI or NVIDIA credential is required for that baseline.

The runtime also contains a hard monetary budget ledger. A zero budget blocks providers that are known to require payment, and unknown provider pricing fails closed rather than silently spending.

## Cloudflare cockpit

Current `wrangler.toml` declares a Worker and static assets only. It does not declare D1, KV, R2, Durable Objects, Workers AI, Queues or another paid data binding.

Cloudflare currently documents a Workers Free plan with 100,000 requests per day and a 10 ms CPU limit per request. Therefore the current cockpit can remain USD 0 **only while the account remains on the Free plan and usage stays inside the applicable free limits**.

Primary pricing source checked 2026-10-06:

- https://www.cloudflare.com/plans/

The repository must not describe Cloudflare hosting as unconditionally free forever; provider quotas and plan terms can change.

## GitHub Actions

GitHub currently documents standard GitHub-hosted runners as free for public repositories. The current `Mimicus CI` uses a standard Ubuntu runner, not a larger paid runner.

Primary source checked 2026-10-06:

- https://docs.github.com/en/billing/concepts/product-billing/github-actions

If the repository becomes private, uses larger runners, or exceeds separately billed storage/products, this assumption must be re-evaluated.

## Model inference

### Offline profile

`MIMICUS_PROFILE=offline` is the mandatory zero-cost fallback and is the default when no profile is configured.

It is suitable for deterministic orchestration, safety, replay, commercial-policy logic, tests and fixtures. It is not a claim that a scripted provider offers the same general reasoning capability as a hosted frontier model.

### NVIDIA NIM profile

The optional NVIDIA profile targets the OpenAI-compatible NVIDIA NIM endpoint and currently defaults to `deepseek-ai/deepseek-v4.1-flash`.

NVIDIA currently documents free NIM API endpoint access for members of the NVIDIA Developer Program for prototyping. NVIDIA separately states that production use of downloadable NIMs requires NVIDIA AI Enterprise licensing.

Primary sources checked 2026-10-06:

- https://docs.api.nvidia.com/nim/docs/run-anywhere
- https://build.nvidia.com/models

For that reason MiMicus intentionally defaults NVIDIA to `known_zero_cost = false`. The operator may set `MIMICUS_NVIDIA_KNOWN_ZERO_COST=1` only after verifying that the exact hosted endpoint/session is currently entitled to free development/prototyping use.

This makes hosted real-model inference **optionally USD 0 for qualifying development/prototyping**, but it is not a perpetual or production-wide USD 0 guarantee.

### OpenAI profile

The OpenAI profile is optional and is not part of the mandatory USD 0 baseline. It must never be treated as free unless authoritative pricing/entitlement evidence says so.

## What “USD 0” means for MiMicus

A valid USD 0 claim means all of the following are true for the run or deployment being discussed:

1. no mandatory paid SaaS dependency is required;
2. the selected provider is offline/local or explicitly verified as zero-cost for that usage;
3. monetary budget is zero or bounded by an explicit operator decision;
4. Cloudflare remains inside the Free-plan conditions if the public cockpit is used;
5. GitHub CI remains on a free-eligible runner/repository configuration;
6. no optional paid effect, browser, sandbox, database, model or observability adapter has been enabled.

If any condition is unknown, the evidence label is `UNKNOWN`, not `USD 0 VERIFIED`.
