# Allora-Edge

Allora-Edge is an ORDER-001 **zero-key, zero-transaction, read-only** radar for the Allora Network. It discovers topics dynamically, records live topic state, classifies topic objectives, applies a fail-closed business eligibility gate, tracks lifecycle transitions, exposes worker/reward telemetry, and provides a generic non-trading shadow-worker framework without submitting anything on-chain.

Current business constraint: no trading, arbitrage, crypto-price/log-return/volatility signals, DeFi alpha, marketing, sales, own customers, or manual job hunting. Financial topics are telemetry-only and cannot be passed to the shadow model engine.

## Safety invariant

`LIVE_EXECUTION_PROHIBITED_BY_ORDER_001`

The code contains no signer, wallet, transaction builder, faucet, registration, funding, staking, delegation, or inference-submission path. The HTTP client permits HTTPS GET reads only and rejects write-like paths/operations.

## Current network compatibility

| Network | Chain ID | Deployed chain | Emissions API |
|---|---|---:|---:|
| mainnet | `allora-mainnet-1` | `v0.16.0` | `v9` |
| testnet | `allora-testnet-1` | `v0.17.0` | `v10` |

The client selects the API namespace from an explicit network manifest and verifies chain ID before scans. See `docs/NETWORK_COMPATIBILITY.md`.

## Install / run

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
allora-edge scan
allora-edge watch --interval 60
allora-edge census
allora-edge topic 1
allora-edge economics 1
allora-edge workers 1
allora-edge replay --from-height 10300000 --to-height 10310000 --step 1000
allora-edge report
allora-edge benchmark --requests 10
allora-edge shadow-demo
allora-edge health
allora-edge safety-check --root .
```

Default state DB: `.allora-edge/allora-edge.sqlite3`. Deterministic exports go to `evidence/`.

Container equivalent:

```bash
docker build -t allora-edge .
docker run --rm -v "$PWD/evidence:/app/evidence" allora-edge scan
```

No wallet setup or secret is needed for chain RPC/LCD reads. The separately documented consumer API (`api.allora.network`) requires an API key and is not used by ORDER-001.

## Current 2026-08-10 census checkpoint

`NEXT_TOPIC_ID=24`; existing topics `1..23`; active topics `15`; active non-trading topics `0`; qualifying topics `0`. Every live topic objective observed is crypto price/log-return/volatility. All checked topic worker-whitelist switches are enabled. Therefore the independent Gate-0 is confirmed and terminal business posture is `DORMANT_READY`, not a worker deployment target.

The watcher does not hardcode those counts. Every live scan starts from `next_topic_id`.

## Tests

```bash
PYTHONPATH=src python -m unittest discover -s tests -v  # 33 tests at ORDER-001 checkpoint
python -m compileall -q src tests
PYTHONPATH=src python -m allora_edge.cli safety-check --root .
```

GitHub CI is prepared in `.github/workflows/ci.yml`; ORDER-001 does not require consuming hosted CI capacity.
