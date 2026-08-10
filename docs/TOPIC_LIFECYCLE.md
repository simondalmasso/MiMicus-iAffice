# Topic lifecycle

Canonical analytical states used by ORDER-001:

`CREATED → INACTIVE → ACTIVE → CHURNABLE → WORKER_REQUEST → REPUTER_REQUEST → REWARDABLE → REWARD_DISTRIBUTED`

Evidence routes in mainnet v9 include `is_topic_active`, `next_churning_block_by_topic_id`, worker/reputer submission-window status, unfulfilled nonces, topic commit info, and topic reward nonce. A scan records first/last seen topic state and transition events. It emits `NEW_TOPIC`, `TOPIC_ACTIVATED`, `TOPIC_DEACTIVATED`, `TOPIC_NOW_CHURNABLE`, `TOPIC_REWARDABLE`, whitelist/revenue changes, and qualifying-topic events.

The state model is observational, not a substitute for chain consensus. Missing state remains unknown; it never creates eligibility.
