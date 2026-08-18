from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from mimicus.canonical import sha256_obj, sha256_text


@dataclass(frozen=True)
class AgentIdentity:
    fingerprint: str
    lineage_id: str
    provider: str
    model_family: str
    phenotype: str
    tool_policy_hash: str
    runtime_model_version: str = "unknown"
    phenotype_version: str = "v1"
    system_prompt_hash: str = ""
    tool_manifest_hash: str = ""
    policy_hash: str = ""
    provider_adapter_version: str = "unknown"
    parent_fingerprint: str | None = None
    revision_provenance: str = "source-controlled builtin"
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            object.__setattr__(self, "created_at", datetime.now(UTC).isoformat())
        if not self.system_prompt_hash:
            object.__setattr__(self, "system_prompt_hash", sha256_text(f"{self.phenotype}:{self.phenotype_version}"))
        if not self.tool_manifest_hash:
            object.__setattr__(self, "tool_manifest_hash", self.tool_policy_hash)
        if not self.policy_hash:
            object.__setattr__(self, "policy_hash", sha256_text("mimicus-v0.2.1-policy"))

    @property
    def manifest_hash(self) -> str:
        return sha256_obj(
            self.material_manifest
            | {"fingerprint": self.fingerprint, "lineage_id": self.lineage_id, "parent_fingerprint": self.parent_fingerprint, "revision_provenance": self.revision_provenance}
        )

    @property
    def material_manifest(self) -> dict[str, str]:
        return {
            "runtime_provider_id": self.provider,
            "runtime_model_id": self.model_family,
            "runtime_model_version": self.runtime_model_version,
            "phenotype": self.phenotype,
            "phenotype_version": self.phenotype_version,
            "system_prompt_hash": self.system_prompt_hash,
            "tool_manifest_hash": self.tool_manifest_hash,
            "policy_hash": self.policy_hash,
            "provider_adapter_version": self.provider_adapter_version,
        }


def exact_fingerprint(
    *,
    provider: str,
    model: str,
    model_version: str,
    phenotype: str,
    phenotype_version: str,
    system_prompt_hash: str,
    tool_manifest_hash: str,
    policy_hash: str,
    provider_adapter_version: str,
) -> str:
    return sha256_obj(
        {
            "runtime_provider_id": provider,
            "runtime_model_id": model,
            "runtime_model_version": model_version,
            "phenotype": phenotype,
            "phenotype_version": phenotype_version,
            "system_prompt_hash": system_prompt_hash,
            "tool_manifest_hash": tool_manifest_hash,
            "policy_hash": policy_hash,
            "provider_adapter_version": provider_adapter_version,
            "scope": "mimicus-exact-agent-v2.1",
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
    fingerprint: str | None = None,
    provider: str,
    model_family: str,
    phenotype: str,
    tool_policy_hash: str,
    runtime_model_version: str = "unknown",
    phenotype_version: str = "v1",
    system_prompt_hash: str = "",
    tool_manifest_hash: str = "",
    policy_hash: str = "",
    provider_adapter_version: str = "unknown",
    parent_fingerprint: str | None = None,
    declared_lineage_id: str | None = None,
    revision_provenance: str = "source-controlled builtin",
) -> AgentIdentity:
    prompt_hash = system_prompt_hash or sha256_text(f"{phenotype}:{phenotype_version}")
    tools_hash = tool_manifest_hash or tool_policy_hash
    resolved_policy = policy_hash or sha256_text("mimicus-v0.2.1-policy")
    resolved_fp = fingerprint or exact_fingerprint(
        provider=provider,
        model=model_family,
        model_version=runtime_model_version,
        phenotype=phenotype,
        phenotype_version=phenotype_version,
        system_prompt_hash=prompt_hash,
        tool_manifest_hash=tools_hash,
        policy_hash=resolved_policy,
        provider_adapter_version=provider_adapter_version,
    )
    resolved_lineage = declared_lineage_id or lineage_id(provider=provider, model_family=model_family, phenotype=phenotype, tool_policy_hash=tool_policy_hash)
    return AgentIdentity(
        fingerprint=resolved_fp,
        lineage_id=resolved_lineage,
        provider=provider,
        model_family=model_family,
        phenotype=phenotype,
        tool_policy_hash=tool_policy_hash,
        runtime_model_version=runtime_model_version,
        phenotype_version=phenotype_version,
        system_prompt_hash=prompt_hash,
        tool_manifest_hash=tools_hash,
        policy_hash=resolved_policy,
        provider_adapter_version=provider_adapter_version,
        parent_fingerprint=parent_fingerprint,
        revision_provenance=revision_provenance,
    )
