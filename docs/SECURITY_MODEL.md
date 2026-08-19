# Security model

External content is data, never instruction authority. Trust domains are trusted internal state/code, authorized external data, untrusted external data and the explicit reference fixture.

The strongest boundary is physical: agents and `aria-core` cannot possess external write credentials or call write-capable vendor APIs. Specialists emit typed `ActionIntent` records only. `aria-effects` is internal-only over a Cloudflare Service Binding and is the sole write-capable component. It contains no model/planner role and cannot invent operations.

Every protected intent binds actor, subject, connector, operation, target, canonical parameters, schema/policy versions and precondition witness into `action_digest`. Approval is deterministic, signed, one-time and bound to that digest. Parameter mutation, stale policy, stale precondition, forged approval, replay and authority expansion fail closed.

State plus outbox intent is committed with one D1 `batch()` transaction. Effect execution is idempotent; duplicate delivery produces one observable effect. A provider idempotency key protects retries after external success but before local acknowledgement, while `effect_receipts` protect normal replay. Free quota exhaustion records `RETRYABLE`; there is no paid failover.

Other controls include bearer-authenticated mutation endpoints, webhook signatures and replay keys, request size limits, Durable Object rate windows, HTTPS/hostname allowlists, private-network SSRF rejection, secret redaction, no credentials in model-visible context, CSP/no-store/nosniff headers, paid-model denylist, Queue retry/DLQ and deterministic evidence.

`scripts/architecture-guard.mjs` fails if external write credential names or write-capable external `fetch()` paths occur outside the effect boundary, or if model/planner bindings occur in `aria-effects`.
