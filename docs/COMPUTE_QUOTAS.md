# Compute quota and reservation model

Free quotas are authority boundaries, not telemetry hints. Each `QuotaPool` stores a provider/model scope, dimension, authoritative verified Free ceiling, local hard fraction, consumed, reserved, upstream remaining/reset metadata and the evidence ID supporting the ceiling.

`localHardFraction` is capped at 0.80. `verifiedFreeCeiling=null` means no reservation is allowed. Provider response headers may update observed health/remaining metadata only after policy validation; they never raise the authoritative verified ceiling by themselves.

`ComputeGovernorDO` is the deployment concurrency boundary. SQLite operations execute in the single Durable Object instance for `global-compute-market`; reservation existence/check/update/insert occur without an await between check and mutation. Idempotency keys collapse retries. Expired reservations release reserved capacity. Success commits actual usage. Unknown completion is conservatively charged at least the reserved amount before retry/fallback, preventing duplicate requests from exceeding Free capacity.

A reservation is required before model execution. A failed reservation produces `QUOTA_RESERVATION_FAILED`/`FREE_QUOTA_EXHAUSTED`; routing may try another independently eligible pool or defer. It never crosses into billable capacity.
