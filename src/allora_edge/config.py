from __future__ import annotations

from .models import NetworkSpec

NETWORKS: dict[str, NetworkSpec] = {
    "mainnet": NetworkSpec(
        name="mainnet",
        chain_id="allora-mainnet-1",
        deployed_version="v0.16.0",
        emissions_api="v9",
        rpc="https://allora-rpc.mainnet.allora.network",
        lcd="https://allora-api.mainnet.allora.network",
        grpc="https://allora-grpc.mainnet.allora.network",
        explorer="https://explorer.allora.network/",
    ),
    "testnet": NetworkSpec(
        name="testnet",
        chain_id="allora-testnet-1",
        deployed_version="v0.17.0",
        emissions_api="v10",
        rpc="https://allora-rpc.testnet.allora.network",
        lcd="https://allora-api.testnet.allora.network",
        grpc="https://allora-grpc.testnet.allora.network",
        explorer="https://explorer.testnet.allora.network/allora-testnet-1",
    ),
}

SCHEMA_VERSION = 1
ORDER_ID = "ORDER-001"
WRITE_LOCK_ERROR = "LIVE_EXECUTION_PROHIBITED_BY_ORDER_001"
