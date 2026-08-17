from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    profile: str = "offline"
    database_url: str = "sqlite:///./mimicus.db"
    max_agents: int = 5
    max_tests: int = 4
    information_floor: float = 0.05
    max_latency_ms: int = 30_000
    openai_model: str = "gpt-5-mini"

    @classmethod
    def from_env(cls, profile: str | None = None) -> Settings:
        resolved = profile or os.environ.get("MIMICUS_PROFILE") or "offline"
        return cls(
            profile=resolved,
            database_url=os.getenv("DATABASE_URL", "sqlite:///./mimicus.db"),
            max_agents=int(os.getenv("MIMICUS_MAX_AGENTS", "5")),
            max_tests=int(os.getenv("MIMICUS_MAX_TESTS", "4")),
            information_floor=float(os.getenv("MIMICUS_INFORMATION_FLOOR", "0.05")),
            max_latency_ms=int(os.getenv("MIMICUS_MAX_LATENCY_MS", "30000")),
            openai_model=os.getenv("MIMICUS_OPENAI_MODEL", "gpt-5-mini"),
        )

    def validate(self) -> None:
        if self.profile not in {"offline", "openai", "test"}:
            raise ValueError(f"unknown profile: {self.profile}")
        if not 1 <= self.max_agents <= 8:
            raise ValueError("max_agents must be in 1..8")
        if self.max_tests < 1:
            raise ValueError("max_tests must be positive")
        if self.information_floor < 0:
            raise ValueError("information_floor must be non-negative")
