# Evidence index

Primary evidence sources:

1. Official Allora Networks documentation — chain IDs, deployed versions, API namespaces, RPC/LCD/gRPC/explorer.
2. `allora-network/allora-chain` tag `v0.16.0`, reference commit `8cbbba6ebe15edad2bcf1adab72eb67cb4568a08` — deployed mainnet query/registration semantics.
3. Official mainnet LCD `emissions/v9` — `next_topic_id`, topic records, active flags, whitelist flags, fee revenue, submission windows, scores.
4. Official mainnet/testnet RPC `/status` — chain identity and live head.
5. Official Allora tokenomics — inference fee and emissions semantics.
6. Official Allora Pairpoint/Vodafone PoC post — non-trading domain specification evidence only, never mainnet economics.

Generated artifacts:
- `evidence/run-metadata.json`
- `evidence/network.json`
- `evidence/topics.json`
- `evidence/topic-census.csv`
- `evidence/classifications.csv`
- `evidence/eligibility.csv`
- `evidence/workers.csv`
- `evidence/rewards.csv`
- `evidence/economics.csv`
- `evidence/incidents.json`
- `evidence/QUALIFYING_TOPICS.json`

Evidence tags are constrained to `LIVE_MAINNET`, `OFFICIAL_CODE`, `OFFICIAL_DOC`, `DERIVED`, `SYNTHETIC_FIXTURE`, `ASSUMPTION`, `UNKNOWN`.
