from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class GateEvidence:
    external_demand_evidence: bool | None = None
    liquid_reward_mechanism: bool | None = None
    entry_cost_under_100: bool | None = None
    source_urls: tuple[str, ...] = ()
    reviewed: bool = False


class GateEvidenceRegistry:
    """Auditable non-secret evidence inputs that chain state alone cannot prove."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else None
        self._topics: dict[str, dict[str, Any]] = {}
        if self.path and self.path.exists():
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                self._topics = raw.get("topics", {}) if isinstance(raw.get("topics", {}), dict) else {}

    def for_topic(self, topic_id: int) -> GateEvidence:
        raw = self._topics.get(str(topic_id), {})
        if not isinstance(raw, dict) or raw.get("reviewed") is not True:
            return GateEvidence()
        return GateEvidence(
            external_demand_evidence=_bool_or_none(raw.get("external_demand_evidence")),
            liquid_reward_mechanism=_bool_or_none(raw.get("liquid_reward_mechanism")),
            entry_cost_under_100=_bool_or_none(raw.get("entry_cost_under_100")),
            source_urls=tuple(str(x) for x in raw.get("source_urls", []) if isinstance(x, str)),
            reviewed=True,
        )


def _bool_or_none(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None
