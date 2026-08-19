# Architecture

AriaOS is a Cloudflare-native, event-driven business control plane with a strict physical effect boundary.

`aria-core` owns ingress, deterministic projections, agents, model routing, AUD, policy, approvals, cockpit API, scheduling and canonical D1 memory. It has Workers AI, Queues, Workflows, a SQLite-backed Durable Object coordinator, static cockpit assets and a private Service Binding named `EFFECTS`. It has no external write credentials.

`aria-effects` is a separate Worker with `workers_dev=false` and no public route. It has no Workers AI, planner, agent roles, Workflow or Durable Object bindings. It accepts only typed `ActionIntent` execution through the Service Binding, revalidates action digest, canonical signed approval, policy/approval version, expiry and precondition witness, then calls a small allowlisted effect adapter. Side-effecting vendor calls exist only under `packages/effects` / `apps/effects-worker`.

Canonical path:

`INPUT → SQL/RULES/AGENTS → CLAIM/DECISION → ActionIntent → PolicyEngine → AUD as required → digest-bound approval → D1 atomic state+outbox batch → aria-effects → idempotent effect → effect_receipt/result event → ledger/replay`.

D1 is the system of record. `action_intents` and `effect_receipts` are durable outbox/receipt tables. If dispatch, Queue or a Free quota fails, the committed intent remains `PENDING/RETRYABLE`; core never bypasses the gateway. D1 `batch()` is used for the state+intent transaction.

Required read connectors remain isolated from authority: authenticated webhook ingest, allowlisted REST reads, GitHub reads, Notion mirror planning, CSV import/export and optional Swarm delegation. Notion/GitHub writes are effect adapters only. The reference SafeOutbound effect is idempotent and never contacts a real customer.
