# Decision input

## Current independent recheck — 2026-08-10

- Mainnet chain: `allora-mainnet-1`, deployed `v0.16.0`, emissions `v9`.
- `NEXT_TOPIC_ID=24`; existing IDs `1..23`.
- Active IDs: `1,2,3,9,10,14,15,16,17,18,19,20,21,22,23` (15).
- Every observed topic objective is crypto price/log-return/volatility → `TRADING`.
- Active non-trading topics: `0`.
- Qualifying topics: `0`.
- All topic worker-whitelist switches queried for IDs 1..23 are enabled.
- Real public mainnet/testnet RPC and LCD reads work without wallet, key, account, card, or API key.

`AUD_GATE0=CONFIRMED` and `ARQ_TECHNICAL_RECOMMENDATION=DORMANT_READY`.

## Historical replay boundary

The official public RPC is a pruned peer surface rather than a promised archive service. The API route `active_topics_at_block/<height>` returned an empty scheduled-topic list for both current and older sample heights; it cannot be interpreted as a historical full active-set snapshot. ORDER-001 therefore provides replay tooling but does not fabricate 30/90-day state. Full historical competition/reward reconstruction is `PARTIAL_WITH_EXACT_DATA_GAP` until a $0 authoritative archive source is available.

## Sustained runtime boundary

This execution environment cannot hold a 24-hour durable process on the user's behalf and no cloud provisioning is authorized. Watcher code is complete; the bounded implementation/test run is recorded. Continue locally with `allora-edge watch --interval 60`. `SUSTAINED_RUN_BLOCKED_BY_RUNTIME` is an environment limitation, not a permission to buy hosting.
