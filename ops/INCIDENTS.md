# Incidents

Known ORDER-001 limitations are evidence gaps, not silently repaired assumptions:

- `HISTORICAL_ARCHIVE_UNAVAILABLE`: no verified $0 official 30/90-day full historical state/reward source was available through the public endpoints used.
- `CONSUMER_API_AUTH_REQUIRED`: the separate Allora consumer API requires an API key; ORDER-001 does not obtain one.
- `SUSTAINED_RUN_BLOCKED_BY_RUNTIME`: current execution session is not a durable 24h host; no cloud provisioning is authorized.
- `REGISTRATION_FEE_EXACT_VALUE_NOT_EXTRACTED`: current live params response was readable, but the harness excerpt did not expose that trailing field; value remains unknown rather than guessed.
