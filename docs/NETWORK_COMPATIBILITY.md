# Network compatibility

Verified 2026-08-10 from official Allora network documentation:

| Field | Mainnet | Testnet |
|---|---|---|
| Chain ID | `allora-mainnet-1` | `allora-testnet-1` |
| Deployed chain | `v0.16.0` | `v0.17.0` |
| Emissions REST namespace | `v9` | `v10` |
| RPC | `https://allora-rpc.mainnet.allora.network/` | `https://allora-rpc.testnet.allora.network/` |
| LCD | `https://allora-api.mainnet.allora.network/` | `https://allora-api.testnet.allora.network/` |
| gRPC | `https://allora-grpc.mainnet.allora.network/` | `https://allora-grpc.testnet.allora.network/` |
| Explorer | `https://explorer.allora.network/` | `https://explorer.testnet.allora.network/allora-testnet-1` |

Mainnet reference tag `v0.16.0` dereferences to chain source commit `8cbbba6ebe15edad2bcf1adab72eb67cb4568a08`. Mainnet v9 query routes are taken from `x/emissions/proto/emissions/v9/query.proto` at that release.

The networks intentionally differ: v0.17/v10 adds labeled/multi-output inference semantics absent from the deployed v0.16/v9 mainnet. Allora-Edge therefore refuses to infer the API namespace from topic payload shape and selects it from a verified network specification.

Runtime defense: `verify_network()` checks the RPC-returned chain ID. Missing/malformed required fields raise `SchemaMismatch` rather than silently switching schema.
