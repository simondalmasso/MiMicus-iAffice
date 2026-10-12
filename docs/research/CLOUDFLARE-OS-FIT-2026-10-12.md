# Cloudflare OS — architectural fit (2026-10-12)

Source: https://github.com/cloudflare/cloudflare-os

## Verified from upstream

- Cloudflare OS is a full AI productivity platform, not a client library. Its major surfaces are agents, Gadgets (per-user sandboxed apps), and Gatekeepers for controlled external access.
- Gatekeepers broker narrow capabilities, provider authorization, logging, and human approvals. Their proposed workflow supports speculative local simulated outcomes while approvals remain pending.
- The platform is built around Cloudflare Workers, Durable Objects, Dynamic Workers/Facets, and Cap'n Web.
- The upstream README explicitly labels v2 as early access with rough edges; its local `pnpm run-local` path is not presented as a production deployment.
- Repository license: Apache-2.0.
- Cloud deployment, model inference, Durable Objects, Dynamic Workers, and connected external services cannot be assumed to carry a perpetual $0 total cost.

## Mimicus integration decision

**Do not replace MiMicusEngine, DagExecutor, memory authority, or EffectDispatcher with Cloudflare OS.** That would introduce a second orchestration/security platform and replace the existing Python core.

**Adopt patterns only, as separately benchmarked extensions:**

1. Gatekeeper-style narrow, resource-scoped capability grants at the existing Mimicus effect dispatch boundary.
2. A future adapter-mediated approval inbox with sanitized, legible requests.
3. Human approval of a sequence of *simulated* effects is an EXPERIMENT ONLY. Simulation must never be reported as a real send, conversion, reply, or external success; later effects cannot depend on fabricated remote outcomes.
4. Durable Objects as OPTIONAL stateful edge read-model infrastructure if there is a demonstrated remote observability requirement. Not for granting memory or agent authority.
5. Cap'n Web as OPTIONAL RPC alternative after an actual transport need and cost/security evaluation.

## Decision for current release

The cockpit stays static/observational and self-contained. It displays verified local observer events when present, otherwise explicit unavailability. No Cloudflare OS package, Durable Object binding, or new recurring cost is added.

Next falsification before adopting Gatekeeper-like code: compare exact-envelope policy, approval races, UNKNOWN outcomes, least-privilege credentials and post-approval reconciliation against existing Mimicus EffectPolicy tests.

This document describes upstream patterns; no Cloudflare OS source files have been copied into Mimicus.
