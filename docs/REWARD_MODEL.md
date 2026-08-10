# Reward model

Canonical source priority is the deployed `allora-chain` release, then official docs, then derived analytics. Mainnet v0.16.0 reward code selects rewardable active topics by weight, caps them by `MaxActiveTopicsPerBlock`, and in the normal treasury-sufficient path computes each topic's epoch reward as:

`(topic_weight / total_previous_topic_weights) × current_emission_per_block × epoch_length`

A topic without a valid non-zero reward nonce is skipped and its allocated amount is returned to the ecosystem bucket. Participant payout then requires the canonical actor-level distribution, scores/regrets, reward fractions, and other protocol inputs.

`canonical_topic_reward()` implements only that explicit v0.16 main-path topic formula. `simulate_reward()` decides `WOULD_BE_ACTIVE` only from our score versus an observed active-set threshold, and computes `ESTIMATED_ALLO_REWARD` only when an explicit participant reward fraction is supplied. Treasury-cap redistribution, rewardable-topic selection, and missing participant fractions are never imputed. Every incomplete result exposes `missing_inputs`.

Historical end-to-end validation remains `PARTIAL_WITH_VALIDATION_GAP`: the current $0 public-history surface did not provide enough authoritative reward-epoch history to compare simulated actor payouts against a 30/90-day corpus.
