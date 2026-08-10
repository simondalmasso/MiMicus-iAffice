# Topic classification

Classes are deterministic: `TRADING`, `NON_TRADING`, `AMBIGUOUS`, `UNKNOWN`.

TRADING requires explicit financial/market semantics such as price prediction, log return, return, volatility, yield, market signal, perp, arbitrage, or DeFi context. Crypto asset references strengthen this determination.

NON_TRADING requires explicit physical/non-market semantics such as energy consumption, state of charge, charger availability, weather, logistics, maintenance, IoT, physical infrastructure availability, traffic flow, equipment failure, or unrelated classification.

Mixed signals become AMBIGUOUS. Insufficient evidence becomes UNKNOWN. Both fail the eligibility gate. No LLM output can silently override the canonical rule result.

2026-08-10 live mainnet: all 23 observed topics are TRADING by explicit metadata; no active NON_TRADING topic exists.
