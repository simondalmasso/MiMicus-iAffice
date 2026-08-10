# Worker competition analytics

Mainnet v9 exposes current lowest inferer/forecaster/reputer scores, per-block worker scores, score EMAs, previous topic quantiles, reward fractions, and network inference payloads containing participant arrays. Allora-Edge provides parsers/helpers for these read paths and concentration statistics (zero-reward share, top-10 share, HHI, P25/P50/P75) when a complete reward sample is available.

The fresh 2026-08-10 evidence package records current lowest inferer-score telemetry for active topics where extracted. This answers the protocol-side active-set threshold question without producing any prohibited financial prediction.

Full 30/90-day worker and reward distributions are `PARTIAL_WITH_EXACT_DATA_GAP`: the current public read path does not expose a convenient complete historical reward ledger, and ORDER-001 forbids provisioning a paid archive/indexer. No missing distribution is imputed.
