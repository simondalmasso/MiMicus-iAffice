# Zero-Cost Compute Market

ORDER-003 replaces static model selection with a deterministic compute control plane. The market never treats a provider name or marketing claim as authority. A candidate progresses through evidence, billing, privacy, capability, benchmark, health and quota gates before a reservation can be created.

Canonical route: `T0/no-model → ModelDataClass → capability/context → provider/model enabled → current first-party free evidence → billing safety → privacy/trust/training/retention → benchmark threshold → health circuit → durable quota reservation → deterministic score → typed InferenceExecution → private aria-models → sanitized InferenceReceipt → quota commit`.

`aria-core` contains no model-provider credential values and has no Workers AI binding. It reaches `aria-models` only through a private Service Binding. `aria-models` contains the fixed provider manifest and is the only domain allowed to hold model-provider credentials or the Workers AI binding. It has no D1, `aria-effects` binding, business-effect adapters, approvals, planner or arbitrary caller-controlled base URL. `aria-effects` remains the only business-write executor from ORDER-002+A1.

Production eligibility is positive-proof only. Current first-party evidence must support price, billing, privacy, terms and catalog claims; credentialed providers additionally require a fresh successful live account probe. Evidence TTL expiration disables new calls. Third-party catalogs and social claims are candidate discovery only. The checked-in OmniRoute discovery reference is pinned to commit `3c9cb21cca443b8caef5aa180827a6989e258a95` and has zero route-activation authority.

The checked-in benchmark corpus has 70 public cases, at least ten in each of seven task classes. Thresholds are frozen in `providerBenchmarks.ts`. Test-only profiles returned by `buildSeedMarket()` carry `evidenceClass=UNKNOWN` and are used only by deterministic tests; production runtime ignores them. Production profiles are persisted only from controlled provider benchmark execution.

Failure is fail-closed: 402/unknown billing disables monetary-risk routes; 401/403 auth opens the circuit; 404 removes the model route; 429/5xx can fall back only to another independently eligible route; unknown price, stale evidence, quota uncertainty, unsafe privacy, secrets, context overflow, failed quality and all-unsafe states return a reason code or defer without paid fallback.
