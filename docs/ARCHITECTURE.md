# Architecture

AriaOS has three physically separated Cloudflare capability domains.

`aria-core` owns ingress, D1 canonical memory, agents, deterministic business/compute routing, PolicyEngine, AUD, approvals, Workflows, Queues, cockpit, Coordinator and ComputeGovernor Durable Objects. It has neither business-write authority nor direct model-provider execution authority.

`aria-effects` remains the private ORDER-002+A1 business-effect kernel. It alone can execute validated business ActionIntents. It has no model execution role.

`aria-models` is the private inference gateway. It accepts typed `InferenceExecution` messages through a Service Binding and uses a fixed internal provider manifest. Callers cannot supply arbitrary provider base URLs. It has no business-effect adapters, approval authority, planner role, or binding to `aria-effects`.

Business writes preserve `ActionIntent → D1 outbox → aria-effects`. Model calls follow `classification/policy → durable free-capacity reservation → route decision → typed inference → aria-models → receipt → quota reconciliation`. Model completion never expands A1 effect authority.

Migration `0002_compute_market.sql` stores provider/model/evidence/health/quota/reservation/route/call/benchmark/incident state. `ComputeGovernorDO` serializes shared reservations. Existing `business_tick` reclaims expired reservations; ORDER-003 adds no cron.
