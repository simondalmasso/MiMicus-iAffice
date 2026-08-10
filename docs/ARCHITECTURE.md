# Architecture

Data flow: public Allora RPC/LCD GET reads → version-aware client → topic census → deterministic classifier → lifecycle/eligibility engines → SQLite snapshots/transitions → deterministic JSON/CSV evidence. The shadow engine is an isolated offline component and has no network write interface.

Core modules:
- `client.py`: network manifest, chain-ID verification, version-specific REST routes, read helpers.
- `radar.py`: dynamic topic discovery and scan/watch orchestration.
- `classify.py`: rule-based `TRADING|NON_TRADING|AMBIGUOUS|UNKNOWN` decision with evidence.
- `eligibility.py`: all-conditions-required gate; any unknown fails closed.
- `lifecycle.py`: state inference and transition events.
- `storage.py`: schema-versioned, WAL-mode SQLite persistence.
- `analytics.py`, `rewards.py`, `economics.py`: conservative analytics that preserve unknown inputs.
- `shadow.py`: generic adapters and no-submit shadow inference lifecycle.
- `safety.py`: write-path rejection and secret scanning.

No module imports signing/key-management libraries. Production logic has no hardcoded topic list; only network compatibility facts are pinned and intended to be reverified before scans.
