# Incident response

Classify incidents as policy/security, canonical-memory, connector, quota, model, queue/workflow, or deployment. First preserve evidence, exact SHA, timestamp, affected task/event IDs and current policy/budget state. Do not mutate credentials from an agent.

For quota exhaustion: halt optional inference, preserve deferred work/cursor, continue critical deterministic safety/reconciliation when possible, and never move to Paid. For connector failure: keep canonical D1 state, retry within configured limits, then surface an incident. For suspected tampering: stop protected actions, run ledger verification/replay and retain the original database/evidence. For leaked credentials: operator rotates them out-of-band and invalidates affected approvals.
