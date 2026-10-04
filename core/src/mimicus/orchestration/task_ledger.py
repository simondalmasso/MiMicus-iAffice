from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class TaskLedger(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task: str
    domain: str
    known_facts: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    constraints: dict[str, object] = Field(default_factory=dict)
    budget_usd: float = 0.0
    plan: list[str] = Field(default_factory=list)
