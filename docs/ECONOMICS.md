# Economics

Allora topic economics have distinct quantities:

- `fee_revenue`: on-chain topic fee revenue.
- `effective_revenue`: a chain-computed effective revenue value used in topic mechanics; it is not automatically monthly customer revenue.
- `topic_stake`: stake associated with topic weight/economics.
- protocol emissions: minted reward component.
- worker rewards: participant reward allocation.

Official tokenomics state that consumers may pay ALLO for inferences and that zero fee payments drive topic weight/rewards toward zero, while protocol emissions also fund rewards. Therefore emissions are not external customer demand.

ORDER-001 sets `EXTERNAL_DEMAND_FRACTION=UNKNOWN` unless both customer-funded and emission-funded components are explicitly reconstructable. It does not divide `effective_revenue` by time or call it revenue per month.

Because there is no qualifying non-trading topic, expected gross/net 30-day economics are not calculated for current prohibited topics.
