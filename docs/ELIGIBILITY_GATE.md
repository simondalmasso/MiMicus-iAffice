# Eligibility gate

`ELIGIBLE(topic)` requires every condition to be true:

- EXISTS
- ACTIVE
- NON_TRADING
- OPEN_TO_UNKNOWN_WORKER
- WORKER_REQUESTS_EXIST
- REWARDABLE
- EXTERNAL_DEMAND_EVIDENCE
- LIQUID_REWARD_MECHANISM
- ENTRY_COST_PLAUSIBLY_UNDER_100

Unknown is not truth. Any false or unknown condition blocks the topic.

On 2026-08-10, mainnet has no active non-trading topic. Additionally, every worker-whitelist-enabled flag queried for topic IDs 1..23 returned true; observed submission-window status for active topics reports the unauthenticated/non-address context as not registered/not whitelisted. This is not evidence that no new worker can ever be admitted; it is evidence that **open admission for an arbitrary unknown worker is not proven**. The gate therefore fails closed.

If a future scan yields a fully qualifying topic, the only action is `OWNER_AUD_REVIEW_REQUIRED`. No registration or transaction path exists in this repository.
