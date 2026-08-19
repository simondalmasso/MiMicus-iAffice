# Provider onboarding

Adding a provider must not change core router logic. The operator performs this checklist:

1. Identify the direct provider or authorized aggregator and assign `provider_type`, `trust_class`, API protocol and a non-secret logical credential alias.
2. Collect current first-party price/free, billing, privacy, TOS and model-catalog evidence. Hash it and assign TTL no longer than policy maximum.
3. Classify free type and billing safety. If price or billing safety is unknown, stop: route remains disabled.
4. Add a fixed internal endpoint and credential mapping to `apps/model-worker/src/providerManifest.ts`. Caller-supplied base URLs/headers are forbidden.
5. Add provider/model registry records and a verified Free quota pool. Hard usable quota must be <=80% of authoritative Free capacity. Unknown quota cannot reserve.
6. For credentialed providers, configure the secret only on `aria-models`; never on `aria-core` or `aria-effects`. Do not print/read the value. Run the sanitized live probe and persist `LIVE_ACCOUNT_PROBE` evidence.
7. Run the public checked-in benchmark corpus through the model gateway with durable reservations. Persist profiles. Route stays ineligible if any frozen task threshold required by its intended role fails.
8. Run privacy/SECRET tests, 402/auth/429/5xx/model-removal tests, quota concurrency tests, architecture guard, secret scan and fallback chaos.
9. Verify cockpit/API surfaces expose only sanitized metadata and emergency disable persists.
10. Only then enable production eligibility. Reverification/TTL expiry can disable it automatically.

Never create accounts by automation, farm quotas, use temporary email, share credentials, reverse-engineer sessions, bypass provider terms, enter a payment card, enable overage or convert a paid balance into a supposed zero-cost route.
