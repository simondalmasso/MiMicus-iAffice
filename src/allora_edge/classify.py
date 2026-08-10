from __future__ import annotations

import re

from .models import Classification, TopicClass

_CRYPTO = re.compile(r"\b(?:btc|eth|sol|xrp|near|bera|bitcoin|ethereum|solana|crypto|token|perp|defi)\b", re.I)
_TRADING = re.compile(r"\b(?:price prediction|price|log returns?|returns?|volatility|directional|yield|market signal|alpha|arbitrage|perp)\b", re.I)
_NON_TRADING = re.compile(
    r"\b(?:energy consumption|state[- ]of[- ]charge|charger availability|charging port|weather|"
    r"logistics|maintenance|iot|infrastructure availability|physical demand|traffic flow|equipment failure|classification)\b",
    re.I,
)


def classify_topic(metadata: str, objective: str | None = None) -> Classification:
    text = " ".join(x for x in (metadata, objective or "") if x).strip()
    trading_hits = sorted({m.group(0).lower() for m in _TRADING.finditer(text)})
    crypto_hits = sorted({m.group(0).lower() for m in _CRYPTO.finditer(text)})
    non_hits = sorted({m.group(0).lower() for m in _NON_TRADING.finditer(text)})

    if trading_hits and (crypto_hits or not non_hits):
        ev = trading_hits + crypto_hits
        return Classification(TopicClass.TRADING, "Explicit market/financial prediction semantics", ev, "HIGH")
    if trading_hits and non_hits:
        return Classification(TopicClass.AMBIGUOUS, "Mixed market and physical-domain semantics require review", trading_hits + non_hits, "MEDIUM")
    if non_hits:
        return Classification(TopicClass.NON_TRADING, "Explicit physical/non-market prediction objective", non_hits, "HIGH")
    if crypto_hits:
        return Classification(TopicClass.AMBIGUOUS, "Crypto asset reference without enough objective evidence", crypto_hits, "LOW")
    return Classification(TopicClass.UNKNOWN, "No deterministic rule has sufficient evidence", [], "LOW")
