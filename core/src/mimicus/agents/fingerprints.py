from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from mimicus.canonical import sha256_obj


class AgentFingerprintInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: str
    model: str
    model_version: str
    system_prompt_hash: str
    tool_manifest_hash: str
    policy_hash: str

    @property
    def fingerprint(self) -> str:
        return sha256_obj(self)
