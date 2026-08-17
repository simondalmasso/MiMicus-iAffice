from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from mimicus.canonical import sha256_obj


@dataclass(frozen=True)
class AgentIdentity:
    fingerprint: str
    lineage_id: str
    provider: str
    model_family: str
    phenotype: str
    tool_policy_hash: str
    parent_fingerprint: str | None = None
    revision_provenance: str = "source-controlled builtin"
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            object.__setattr__(self, "created_at", datetime.now(UTC).isoformat())

    @property
    def manifest_hash(self) -> str:
        return sha256_obj(
            {
                "fingerprint": self.fingerprint,
                "lineage_id": self.lineage_id,
                "provider": self.provider,
                "model_family": self.model_family,
                "phenotype": self.phenotype,
                "tool_policy_hash": self.tool_policy_hash,
                "parent_fingerprint": self.parent_fingerprint,
                "revision_provenance": self.revision_provenance,
            }
        )


def lineage_id(*, provider: str, model_family: str, phenotype: str, tool_policy_hash: str) -> str:
    return sha256_obj(
        {
            "provider": provider,
            "model_family": model_family,
            "phenotype": phenotype,
            "tool_policy_hash": tool_policy_hash,
            "scope": "mimicus-agent-lineage-v1",
        }
    )


def make_identity(
    *,
    fingerprint: str,
    provider: str,
    model_family: str,
    phenotype: str,
    tool_policy_hash: str,
    parent_fingerprint: str | None = None,
    declared_lineage_id: str | None = None,
    revision_provenance: str = "source-controlled builtin",
) -> AgentIdentity:
    resolved_lineage = declared_lineage_id or lineage_id(
        provider=provider,
        model_family=model_family,
        phenotype=phenotype,
        tool_policy_hash=tool_policy_hash,
    )
    return AgentIdentity(
        fingerprint=fingerprint,
        lineage_id=resolved_lineage,
        provider=provider,
        model_family=model_family,
        phenotype=phenotype,
        tool_policy_hash=tool_policy_hash,
        parent_fingerprint=parent_fingerprint,
        revision_provenance=revision_provenance,
    )
