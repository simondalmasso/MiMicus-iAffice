# Event ledger and replay

Each material ledger record stores sequence, kind, referenced stable ID, timestamp, payload hash, previous chain hash and chain hash. Genesis is deterministic. Verification recomputes every link and rejects modified payload/previous/chain hashes.

The local and D1 stores persist the ledger. Replay rebuilds projections from source events and compares state hashes. The reference E2E persists/reloads state, rebuilds projections, verifies hash equality, modifies a copied ledger row and requires verification failure.

CLI: `aria replay [id]` and `aria verify-ledger`. The optional scope argument is recorded even when full event projection is rebuilt; canonical reconstruction always derives from immutable events/snapshot evidence.
