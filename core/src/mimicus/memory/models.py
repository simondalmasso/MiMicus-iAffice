from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from mimicus.types import MemoryStatus


class MemoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memory_id: str = Field(default_factory=lambda: str(uuid4()))
    claim_hash: str
    content: str
    owner_fingerprint: str
    domain: str
    origin_clusters: list[str]
    authority: float = Field(ge=0.0, le=1.0)
    status: MemoryStatus = MemoryStatus.CANDIDATE
    deterministic_verification: bool = False
    verified_clusters: list[str] = Field(default_factory=list)
    derived_from: list[str] = Field(default_factory=list)
    expires_at: datetime | None = None
