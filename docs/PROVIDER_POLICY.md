# Provider policy

Hard invariants: `COST_HARD_CAP_USD=0`, `MODEL_SPEND_AUTHORIZED_USD=0`, `BILLABLE_INFERENCE=DENY`, `UNKNOWN_PRICE=DENY`, `UNKNOWN_BILLING_SAFETY=DENY`, `PAID_FALLBACK=DENY`, `SECRET_DATA_TO_MODEL=DENY`. AriaOS never adds a card, top-up, purchase, subscription, paid balance, plan upgrade or overage capability.

Evidence authority is explicit. `FIRST_PARTY_OFFICIAL_DOC`, `FIRST_PARTY_API`, `FIRST_PARTY_DASHBOARD_OBSERVED`, `FIRST_PARTY_TERMS`, `SOURCE_CODE_OFFICIAL`, and `LIVE_ACCOUNT_PROBE` may support route activation when current. `THIRD_PARTY_CATALOG`, `SOCIAL_POST`, and `UNKNOWN` never authorize production by themselves.

Maximum TTLs are enforced in code: recurring-free price/policy 14 days; promotional free 24 hours; signup-grant balance 1 hour; live health 15 minutes; recurring catalog 7 days; promotional catalog 24 hours; privacy/TOS 14 days. Trials are not a production default.

Data classes: PUBLIC can use any otherwise eligible provider; INTERNAL_BUSINESS requires first-party direct or explicitly authorized aggregator plus no-training/verified-opt-out and known retention; CONFIDENTIAL further requires strong identity/privacy/retention; SECRET is denied before any model call. Secret detection cannot be downgraded by a caller-provided PUBLIC label.

Current bootstrap: Cloudflare Workers AI has direct recurring-Free evidence and remains subject to live benchmark/quota execution. Groq is candidate-only until a credential-bound Free-account probe succeeds and benchmark qualifies. Mistral remains billing-unsafe until account mode proves no monetary overage path. Gemini Free is PUBLIC_ONLY/TRAINING_ALLOWED and billing-unknown until live account verification. ZenMux is disabled/quarantined pending first-party proof. Old social offers are discovery signals only.
