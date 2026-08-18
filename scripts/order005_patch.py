from __future__ import annotations

from pathlib import Path


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    Path(path).write_text(text, encoding="utf-8")


def repl(path: str, old: str, new: str, count: int = 1) -> None:
    text = read(path)
    if old not in text:
        raise SystemExit(f"anchor missing in {path}: {old[:100]!r}")
    write(path, text.replace(old, new, count))


# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------
repl("src/mimicus/__init__.py", '__version__ = "0.2.0"', '__version__ = "0.2.2"')
repl("pyproject.toml", 'version = "0.2.0"', 'version = "0.2.2"')

# ---------------------------------------------------------------------------
# Canonical identity manifest + recomputation
# ---------------------------------------------------------------------------
write(
    "src/mimicus/agents/identity.py",
    '''from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from mimicus.canonical import sha256_obj, sha256_text

IDENTITY_SCOPE = "mimicus-exact-agent-v2.2"


def material_manifest(
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
) -> dict[str, str]:
    return {
        "runtime_provider_id": provider,
        "runtime_model_id": model,
        "runtime_model_version": model_version,
        "phenotype": phenotype,
        "phenotype_version": phenotype_version,
        "system_prompt_hash": system_prompt_hash,
        "tool_manifest_hash": tool_manifest_hash,
        "policy_hash": policy_hash,
        "provider_adapter_version": provider_adapter_version,
    }


def exact_fingerprint_from_manifest(manifest: dict[str, str]) -> str:
    return sha256_obj({"scope": IDENTITY_SCOPE, "material_manifest": manifest})


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
    return exact_fingerprint_from_manifest(
        material_manifest(
            provider=provider,
            model=model,
            model_version=model_version,
            phenotype=phenotype,
            phenotype_version=phenotype_version,
            system_prompt_hash=system_prompt_hash,
            tool_manifest_hash=tool_manifest_hash,
            policy_hash=policy_hash,
            provider_adapter_version=provider_adapter_version,
        )
    )


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
            object.__setattr__(self, "policy_hash", sha256_text("mimicus-v0.2.2-policy"))

    @property
    def material_manifest(self) -> dict[str, str]:
        return material_manifest(
            provider=self.provider,
            model=self.model_family,
            model_version=self.runtime_model_version,
            phenotype=self.phenotype,
            phenotype_version=self.phenotype_version,
            system_prompt_hash=self.system_prompt_hash,
            tool_manifest_hash=self.tool_manifest_hash,
            policy_hash=self.policy_hash,
            provider_adapter_version=self.provider_adapter_version,
        )

    def recompute_fingerprint(self) -> str:
        return exact_fingerprint_from_manifest(self.material_manifest)

    @property
    def fingerprint_matches_manifest(self) -> bool:
        return self.fingerprint == self.recompute_fingerprint()

    @property
    def manifest_hash(self) -> str:
        return sha256_obj(
            {
                "material_manifest": self.material_manifest,
                "fingerprint": self.fingerprint,
                "recomputed_fingerprint": self.recompute_fingerprint(),
                "lineage_id": self.lineage_id,
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
    resolved_policy = policy_hash or sha256_text("mimicus-v0.2.2-policy")
    manifest = material_manifest(
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
    resolved_fp = fingerprint or exact_fingerprint_from_manifest(manifest)
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
''',
)

# Repository rejects mismatched material identity and exposes identity audit state.
repl(
    "src/mimicus/storage/repository.py",
    "    def register_identity(self, identity: AgentIdentity) -> None:\n        with self.engine.begin() as connection:\n",
    "    def register_identity(self, identity: AgentIdentity) -> None:\n        recomputed = identity.recompute_fingerprint()\n        if identity.fingerprint != recomputed:\n            raise ValueError(\"agent fingerprint/material manifest mismatch\")\n        with self.engine.begin() as connection:\n",
)
repl(
    "src/mimicus/storage/repository.py",
    '                    "fingerprint": identity.fingerprint,\n                    "lineage_id": identity.lineage_id,\n',
    '                    "fingerprint": identity.fingerprint,\n                    "recomputed_fingerprint": recomputed,\n                    "fingerprint_matches_manifest": True,\n                    "material_manifest": identity.material_manifest,\n                    "lineage_id": identity.lineage_id,\n',
)
repl(
    "src/mimicus/storage/repository.py",
    "            if fingerprint is None:\n                connection.execute(\n",
    "            if fingerprint is not None:\n                existing_manifest = connection.execute(select(AgentFingerprintRow.manifest_json).where(AgentFingerprintRow.fingerprint == identity.fingerprint)).scalar_one()\n                parsed_manifest = json.loads(existing_manifest)\n                if parsed_manifest.get(\"material_manifest\") != identity.material_manifest or parsed_manifest.get(\"recomputed_fingerprint\") != recomputed:\n                    raise ValueError(\"agent fingerprint manifest drift detected\")\n            if fingerprint is None:\n                connection.execute(\n",
)
repl(
    "src/mimicus/storage/repository.py",
    "            lineages = connection.execute(select(AgentLineageMemberRow.fingerprint, AgentLineageMemberRow.lineage_id)).all()\n            communications: list[str] = []\n",
    "            lineages = connection.execute(select(AgentLineageMemberRow.fingerprint, AgentLineageMemberRow.lineage_id)).all()\n            identity_manifests = connection.execute(select(AgentFingerprintRow.manifest_json)).scalars().all()\n            communications: list[str] = []\n",
)
repl(
    "src/mimicus/storage/repository.py",
    '            "lineages": [{"fingerprint": a, "lineage_id": b} for a, b in lineages],\n',
    '            "lineages": [{"fingerprint": a, "lineage_id": b} for a, b in lineages],\n            "identities": [json.loads(row) for row in identity_manifests],\n',
)

# ---------------------------------------------------------------------------
# Provider request/capability truth
# ---------------------------------------------------------------------------
repl(
    "src/mimicus/providers/base.py",
    "    pricing_metadata_authoritative: bool = False\n",
    "    pricing_metadata_authoritative: bool = False\n    tool_manifest_hash: str = \"no-tools\"\n    evidence_acquisition_available: bool = False\n",
)
repl(
    "src/mimicus/providers/base.py",
    "    verified_memory: tuple[dict[str, Any], ...] = ()\n",
    "    verified_memory: tuple[dict[str, Any], ...] = ()\n    evidence: tuple[dict[str, Any], ...] = ()\n",
)

# OpenAI adapter: actual tool truth, bounded evidence input, ref validation, preflight max.
write(
    "src/mimicus/providers/openai_agents.py",
    '''from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any

from mimicus.canonical import sha256_obj
from mimicus.claims.models import Claim
from mimicus.orchestration.communication import ChallengeRequest, ChallengeResponse
from mimicus.providers.base import Provider, ProviderCapabilities, ProviderRequest, ProviderResponse


@dataclass
class OpenAIAgentsProvider(Provider):
    model: str
    max_turns: int = 3
    timeout_seconds: float = 30.0
    input_usd_per_million_tokens: float | None = None
    output_usd_per_million_tokens: float | None = None
    max_cost_per_call_usd: float | None = None
    max_memory_items: int = 8
    max_memory_chars: int = 6000
    max_evidence_items: int = 16
    max_evidence_chars: int = 60000
    tools: tuple[Any, ...] = field(default_factory=tuple)

    def _tool_manifest(self) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        for tool in self.tools:
            rows.append(
                {
                    "name": str(getattr(tool, "name", type(tool).__name__)),
                    "description": str(getattr(tool, "description", ""))[:500],
                    "type": f"{type(tool).__module__}.{type(tool).__qualname__}",
                }
            )
        return sorted(rows, key=lambda row: (row["name"], row["type"], row["description"]))

    @property
    def capabilities(self) -> ProviderCapabilities:
        authoritative_pricing = self.max_cost_per_call_usd is not None or (
            self.input_usd_per_million_tokens is not None and self.output_usd_per_million_tokens is not None
        )
        tool_manifest = self._tool_manifest()
        return ProviderCapabilities(
            supports_structured_output=True,
            supports_async=True,
            supports_tools=bool(tool_manifest),
            provider_id="openai_agents",
            model_id=self.model,
            version=f"configured:{self.model}",
            adapter_version="openai-agents-0.21.1/mimicus-adapter-v2.2",
            usage_metadata_available=True,
            cancellation="asyncio.wait_for",
            known_zero_cost=False,
            estimated_max_cost_per_call=self.max_cost_per_call_usd,
            pricing_metadata_authoritative=authoritative_pricing,
            tool_manifest_hash=sha256_obj({"tools": tool_manifest}),
            evidence_acquisition_available=bool(tool_manifest),
        )

    def build_agent(self, phenotype: str, domain: str) -> Any:
        from agents import Agent

        instructions = (
            f"You are the {phenotype} phenotype for domain {domain}. "
            "Return only a structured Claim. Treat missing evidence as uncertainty. "
            "Cite only evidence_hash values present in runtime_evidence. Never invent evidence references. "
            "Verified institutional memory is gated context, not a peer answer. "
            "Do not coordinate with peer agents during this sealed first pass."
        )
        kwargs: dict[str, Any] = {
            "name": f"mimicus-{phenotype}",
            "instructions": instructions,
            "model": self.model,
            "output_type": Claim,
        }
        if self.tools:
            kwargs["tools"] = list(self.tools)
        return Agent(**kwargs)

    @staticmethod
    def _usage_numbers(usage: Any) -> tuple[int | None, int | None, int | None]:
        if usage is None:
            return None, None, None
        input_tokens = getattr(usage, "input_tokens", None)
        output_tokens = getattr(usage, "output_tokens", None)
        total_tokens = getattr(usage, "total_tokens", None)
        return (
            int(input_tokens) if isinstance(input_tokens, int) else None,
            int(output_tokens) if isinstance(output_tokens, int) else None,
            int(total_tokens) if isinstance(total_tokens, int) else None,
        )

    def _monetary_cost(self, usage: Any) -> float | None:
        if self.input_usd_per_million_tokens is None or self.output_usd_per_million_tokens is None:
            return None
        input_tokens, output_tokens, _ = self._usage_numbers(usage)
        if input_tokens is None or output_tokens is None:
            return None
        return (input_tokens * self.input_usd_per_million_tokens + output_tokens * self.output_usd_per_million_tokens) / 1_000_000.0

    def _verified_memory_payload(self, memory: tuple[dict[str, Any], ...]) -> list[dict[str, Any]]:
        allowed = {"private_verified", "shared_verified"}
        payload: list[dict[str, Any]] = []
        used_chars = 0
        for item in memory:
            if str(item.get("status", "")) not in allowed:
                continue
            if len(payload) >= self.max_memory_items:
                break
            content = str(item.get("content", ""))[:1200]
            row = {
                "memory_id": str(item.get("memory_id", "")),
                "claim_hash": str(item.get("claim_hash", "")),
                "content": content,
                "authority": float(item.get("authority", 0.0)),
                "origin_clusters": list(item.get("origin_clusters", []))[:8],
                "verified_clusters": list(item.get("verified_clusters", []))[:8],
            }
            encoded = json.dumps(row, sort_keys=True, separators=(",", ":"))
            if used_chars + len(encoded) > self.max_memory_chars:
                break
            payload.append(row)
            used_chars += len(encoded)
        return payload

    def _evidence_payload(self, evidence: tuple[dict[str, Any], ...]) -> list[dict[str, Any]]:
        payload: list[dict[str, Any]] = []
        used_chars = 0
        for item in evidence:
            if len(payload) >= self.max_evidence_items:
                break
            row = {
                "evidence_hash": str(item.get("evidence_hash", "")),
                "origin": str(item.get("origin", "")),
                "source_class": str(item.get("source_class", "")),
                "observed_at": item.get("observed_at"),
                "as_of": item.get("as_of"),
                "independence_cluster": str(item.get("independence_cluster", "")),
                "content": str(item.get("content", ""))[:12000],
                "extracted_facts": item.get("extracted_facts", {}),
                "extraction_method": str(item.get("extraction_method", "")),
                "authority_class": str(item.get("authority_class", "")),
                "units": item.get("units"),
            }
            encoded = json.dumps(row, sort_keys=True, separators=(",", ":"), default=str)
            if used_chars + len(encoded) > self.max_evidence_chars:
                break
            payload.append(row)
            used_chars += len(encoded)
        return payload

    def structured_input(self, request: ProviderRequest) -> tuple[str, int, int]:
        memory = self._verified_memory_payload(request.verified_memory)
        evidence = self._evidence_payload(request.evidence)
        body = {
            "task": request.task,
            "runtime_evidence": evidence,
            "verified_institutional_memory": memory,
            "sealed_first_pass": True,
            "peer_outputs_included": False,
        }
        return json.dumps(body, sort_keys=True, separators=(",", ":"), default=str), len(memory), len(evidence)

    async def generate_async(self, task: str, phenotype: str, domain: str) -> tuple[Claim, dict[str, object]]:
        from agents import Runner

        agent = self.build_agent(phenotype, domain)

        async def invoke() -> Any:
            return await Runner.run(agent, task, max_turns=self.max_turns)

        result = await asyncio.wait_for(invoke(), timeout=self.timeout_seconds)
        output = result.final_output
        if not isinstance(output, Claim):
            output = Claim.model_validate(output)
        usage = getattr(getattr(result, "context_wrapper", None), "usage", None)
        input_tokens, output_tokens, total_tokens = self._usage_numbers(usage)
        cost = self._monetary_cost(usage)
        metadata: dict[str, object] = {
            "last_agent": getattr(getattr(result, "last_agent", None), "name", None),
            "usage": str(usage) if usage is not None else None,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "timeout_seconds": self.timeout_seconds,
            "monetary_cost_status": "KNOWN" if cost is not None else "UNKNOWN",
        }
        if cost is not None:
            metadata["monetary_cost_usd"] = cost
        return output, metadata

    async def generate_request_async(self, request: ProviderRequest) -> ProviderResponse:
        started = perf_counter()
        model_input, memory_count, evidence_count = self.structured_input(request)
        claim, metadata = await self.generate_async(model_input, request.phenotype, request.domain)
        latency_ms = (perf_counter() - started) * 1000.0
        trace_id = str(metadata.get("last_agent") or "") or None
        allowed = {str(item.get("evidence_hash", "")) for item in request.evidence}
        claimed = list(dict.fromkeys(claim.evidence_refs))
        validated = [ref for ref in claimed if ref in allowed]
        rejected = [ref for ref in claimed if ref not in allowed]
        validated_claim = claim.model_copy(update={"evidence_refs": validated})
        usage = dict(metadata)
        usage.update(
            {
                "verified_memory_items_consumed": memory_count,
                "evidence_items_supplied": evidence_count,
                "evidence_hashes_supplied": sorted(allowed),
                "evidence_refs_claimed": claimed,
                "evidence_refs_validated": validated,
                "evidence_refs_rejected": rejected,
            }
        )
        cost_value = usage.get("monetary_cost_usd")
        cost = float(cost_value) if isinstance(cost_value, (float, int)) else None
        return ProviderResponse(claim=validated_claim, cost=cost, latency_ms=latency_ms, trace_id=trace_id, usage=usage)

    async def challenge_async(self, request: ChallengeRequest) -> ChallengeResponse:
        from agents import Agent, Runner

        kwargs: dict[str, Any] = {
            "name": "mimicus-structured-challenger",
            "instructions": "Evaluate only the supplied structured claim/evidence/falsifier summary. Return a concise ChallengeResponse. Never expose hidden chain-of-thought.",
            "model": self.model,
            "output_type": ChallengeResponse,
        }
        if self.tools:
            kwargs["tools"] = list(self.tools)
        agent = Agent(**kwargs)
        result = await asyncio.wait_for(Runner.run(agent, request.model_dump_json(), max_turns=self.max_turns), timeout=self.timeout_seconds)
        output = result.final_output
        response = output if isinstance(output, ChallengeResponse) else ChallengeResponse.model_validate(output)
        call_id = getattr(getattr(result, "last_agent", None), "name", None)
        usage_obj = getattr(getattr(result, "context_wrapper", None), "usage", None)
        input_tokens, output_tokens, total_tokens = self._usage_numbers(usage_obj)
        cost = self._monetary_cost(usage_obj)
        usage = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "monetary_cost_status": "KNOWN" if cost is not None else "UNKNOWN",
        }
        return response.model_copy(update={"provider_call_id": str(call_id) if call_id else response.provider_call_id, "cost": cost, "usage": usage})
''',
)

# Profiles read explicit cost/pricing configuration.
repl(
    "src/mimicus/plugins/profiles.py",
    "PROFILES = {\n",
    '''def _env_float(name: str) -> float | None:
    value = os.getenv(name)
    if value is None or not value.strip():
        return None
    parsed = float(value)
    if parsed < 0:
        raise ValueError(f"{name} must be non-negative")
    return parsed


PROFILES = {
''',
)
repl(
    "src/mimicus/plugins/profiles.py",
    '    provider: Provider = provider_override or (ScriptedProvider() if profile_name != "openai" else OpenAIAgentsProvider(os.getenv("MIMICUS_OPENAI_MODEL", "gpt-5-mini")))\n',
    '''    provider: Provider = provider_override or (
        ScriptedProvider()
        if profile_name != "openai"
        else OpenAIAgentsProvider(
            os.getenv("MIMICUS_OPENAI_MODEL", "gpt-5-mini"),
            input_usd_per_million_tokens=_env_float("MIMICUS_OPENAI_INPUT_USD_PER_MILLION_TOKENS"),
            output_usd_per_million_tokens=_env_float("MIMICUS_OPENAI_OUTPUT_USD_PER_MILLION_TOKENS"),
            max_cost_per_call_usd=_env_float("MIMICUS_OPENAI_MAX_COST_PER_CALL_USD"),
        )
    )
''',
)

# ---------------------------------------------------------------------------
# Agent factory: canonical identity and actual tool manifest bound
# ---------------------------------------------------------------------------
repl("src/mimicus/plugins/services.py", "from mimicus.canonical import sha256_text\n", "from mimicus.canonical import sha256_obj, sha256_text\n")
repl("src/mimicus/plugins/services.py", '    policy_version: str = "mimicus-v0.2.1-policy"\n', '    policy_version: str = "mimicus-v0.2.2-policy"\n')
repl(
    "src/mimicus/plugins/services.py",
    '            tool_hash = sha256_text(f"tools:{role_version}:{\',\'.join(sorted(capabilities))}")\n',
    '            tool_hash = sha256_obj({"phenotype": role_version, "declared_capabilities": sorted(capabilities), "provider_tool_manifest_hash": caps.tool_manifest_hash})\n',
)
repl(
    "src/mimicus/plugins/services.py",
    "                provider_adapter_version=caps.version,\n",
    "                provider_adapter_version=caps.adapter_version,\n",
)

# ---------------------------------------------------------------------------
# Capability-specific coalition authority
# ---------------------------------------------------------------------------
repl(
    "src/mimicus/coalition/selector.py",
    '    runtime_model_version: str = "unknown"\n',
    '    runtime_model_version: str = "unknown"\n    capability_audition_scores: dict[str, float] = field(default_factory=dict)\n    capability_calibration_scores: dict[str, float] = field(default_factory=dict)\n    capability_states: dict[str, str] = field(default_factory=dict)\n',
)
start = read("src/mimicus/coalition/selector.py").index("def select_coalition(")
prefix = read("src/mimicus/coalition/selector.py")[:start]
write(
    "src/mimicus/coalition/selector.py",
    prefix
    + '''def _capability_state(candidate: AgentCandidate, capability: str) -> str:
    if candidate.capability_states:
        return candidate.capability_states.get(capability, "ACTIVE")
    if candidate.bankrupt:
        return "BANKRUPT"
    if candidate.probation:
        return "PROBATION"
    return "ACTIVE"


def _capability_trust(candidate: AgentCandidate, capability: str) -> float:
    audition_score = candidate.capability_audition_scores.get(capability, candidate.audition_score)
    calibration_score = candidate.capability_calibration_scores.get(capability, candidate.calibration_score)
    return 0.55 * audition_score + 0.45 * calibration_score


def _usable_capabilities(candidate: AgentCandidate, required: set[str]) -> set[str]:
    return {cap for cap in required & set(candidate.capabilities) if _capability_state(candidate, cap) == "ACTIVE"}


def select_coalition(profile: ThreatProfile, candidates: list[AgentCandidate], max_agents: int) -> tuple[list[AgentCandidate], dict[str, object]]:
    required = set(profile.required_capabilities)
    available = [candidate for candidate in candidates if _usable_capabilities(candidate, required)]
    selected: list[AgentCandidate] = []
    uncovered = set(required)
    proximity_log: list[dict[str, object]] = []
    while uncovered and len(selected) < max_agents:
        best: AgentCandidate | None = None
        best_score = -1.0
        for candidate in available:
            if candidate in selected:
                continue
            useful_caps = _usable_capabilities(candidate, uncovered)
            if not useful_caps:
                continue
            corr_penalty = max((correlation(candidate, member) for member in selected), default=0.0)
            proximity_penalty = 0.0
            proximity_reason = "first useful candidate"
            if selected:
                comparisons = [semantic_proximity(_signature(candidate), _signature(member)) for member in selected]
                closest = max(comparisons, key=lambda row: row.score)
                proximity_penalty = 0.45 * closest.score if not closest.useful_contradiction else 0.0
                proximity_reason = closest.reason
            capability_trust = {cap: _capability_trust(candidate, cap) for cap in sorted(useful_caps)}
            authority = sum(capability_trust.values())
            score = authority * (1.0 - 0.8 * corr_penalty) * max(0.05, 1.0 - proximity_penalty)
            proximity_log.append(
                {
                    "candidate": candidate.fingerprint,
                    "capability_coverage": sorted(useful_caps),
                    "capability_trust": capability_trust,
                    "correlation_penalty": corr_penalty,
                    "proximity_penalty": proximity_penalty,
                    "reason": proximity_reason,
                    "marginal_score": score,
                }
            )
            if score > best_score:
                best_score, best = score, candidate
        if best is None:
            break
        selected.append(best)
        uncovered -= _usable_capabilities(best, uncovered)
    rationale: dict[str, object] = {
        "required_capabilities": sorted(required),
        "covered_capabilities": sorted(required - uncovered),
        "uncovered_capabilities": sorted(uncovered),
        "selected": [candidate.fingerprint for candidate in selected],
        "correlation_matrix": {f"{a.fingerprint}:{b.fingerprint}": correlation(a, b) for i, a in enumerate(selected) for b in selected[i + 1 :]},
        "semantic_proximity": proximity_log,
        "capability_authority": {
            candidate.fingerprint: {
                cap: {
                    "state": _capability_state(candidate, cap),
                    "audition_score": candidate.capability_audition_scores.get(cap, candidate.audition_score),
                    "calibration_score": candidate.capability_calibration_scores.get(cap, candidate.calibration_score),
                    "direct_trust": _capability_trust(candidate, cap),
                }
                for cap in sorted(required & set(candidate.capabilities))
            }
            for candidate in candidates
        },
        "probation_excluded": [candidate.fingerprint for candidate in candidates if all(_capability_state(candidate, cap) == "PROBATION" for cap in required & set(candidate.capabilities)) and required & set(candidate.capabilities)],
        "bankrupt_excluded": [candidate.fingerprint for candidate in candidates if all(_capability_state(candidate, cap) == "BANKRUPT" for cap in required & set(candidate.capabilities)) and required & set(candidate.capabilities)],
    }
    return selected, rationale
''',
)

# ---------------------------------------------------------------------------
# Engine: explicit evidence lanes, all-capability auditions, evidence ref binding,
# capability communication trust, online pricing preflight.
# ---------------------------------------------------------------------------
repl(
    "src/mimicus/orchestration/engine.py",
    "from mimicus.claims.evidence import evidence_row, execution_evidence, fixture_evidence\n",
    "from mimicus.claims.evidence import evidence_row, execution_evidence\nfrom mimicus.claims.evidence_bundle import EvidenceInput, explicit_fixture_bundle, runtime_evidence_bundle\n",
)
repl(
    "src/mimicus/orchestration/engine.py",
    '    scenario: str | None = None\n    fixture: dict[str, Any] = Field(default_factory=dict)\n',
    '    scenario: str | None = None\n    fixture: dict[str, Any] = Field(default_factory=dict)\n    source_mode: Literal["runtime", "fixture", "benchmark"] = "runtime"\n    evidence: list[EvidenceInput] = Field(default_factory=list, max_length=16)\n',
)
# Remove lexical auto fixtures entirely.
old_start = read("src/mimicus/orchestration/engine.py").index("def scenario_fixture(")
old_end = read("src/mimicus/orchestration/engine.py").index("\n\ndef _spec_keys", old_start)
engine_text = read("src/mimicus/orchestration/engine.py")
engine_text = (
    engine_text[:old_start]
    + '''def scenario_fixture(request: RunRequest) -> tuple[str, dict[str, Any]]:
    """Return only explicitly supplied fixture material; task words never create facts."""
    if request.fixture:
        return request.scenario or "custom_fixture", dict(request.fixture)
    return request.scenario or "runtime", {}
'''
    + engine_text[old_end:]
)
write("src/mimicus/orchestration/engine.py", engine_text)
repl(
    "src/mimicus/orchestration/engine.py",
    "        scenario, fixture = scenario_fixture(request)\n        ledger = EventLedger(run_id)\n",
    '''        scenario, fixture = scenario_fixture(request)
        resolved_source_mode: Literal["runtime", "fixture", "benchmark"]
        if request.source_mode == "benchmark":
            resolved_source_mode = "benchmark"
        elif request.fixture or request.source_mode == "fixture":
            resolved_source_mode = "fixture"
        else:
            resolved_source_mode = "runtime"
        if resolved_source_mode == "runtime":
            evidence_bundle = runtime_evidence_bundle(run_id, request.evidence)
        else:
            evidence_bundle = explicit_fixture_bundle(
                run_id,
                fixture,
                domain=domain,
                scenario=scenario,
                benchmark=resolved_source_mode == "benchmark",
            )
        falsifier_context = evidence_bundle.falsifier_context()
        ledger = EventLedger(run_id)
''',
)
repl(
    "src/mimicus/orchestration/engine.py",
    '        task_hash = sha256_obj({"task": request.task, "domain": domain, "fixture": fixture})\n',
    '        task_hash = sha256_obj({"task": request.task, "domain": domain, "source_mode": resolved_source_mode, "evidence_hashes": evidence_bundle.hashes, "fixture_hash": sha256_obj(fixture) if resolved_source_mode != "runtime" else None})\n',
)
repl(
    "src/mimicus/orchestration/engine.py",
    '                "learn": request.learn,\n',
    '                "learn": request.learn,\n                "source_mode": resolved_source_mode,\n',
)
repl(
    "src/mimicus/orchestration/engine.py",
    '        ledger.append("run_started", {"task_hash": task_hash, "config_hash": config_hash, "plugin_hashes": self.plugin_hashes})\n',
    '        ledger.append("run_started", {"task_hash": task_hash, "config_hash": config_hash, "plugin_hashes": self.plugin_hashes, "source_mode": resolved_source_mode})\n        ledger.append("evidence_bundle_prepared", {"source_mode": resolved_source_mode, "evidence_hashes": list(evidence_bundle.hashes), "count": len(evidence_bundle.items)})\n',
)
# Identity revisions: canonical unless an explicit supplied fp (which repository will reject if mismatched).
old = '''                revised_fp = str(
                    revision.get("fingerprint") or _fingerprint(candidate.name, candidate.provider, candidate.model, prompt=str(revision.get("prompt_revision", "revision")))
                )
                identity = make_identity(
                    fingerprint=revised_fp,
'''
new = '''                requested_fp = str(revision["fingerprint"]) if revision.get("fingerprint") else None
                identity = make_identity(
                    fingerprint=requested_fp,
'''
repl("src/mimicus/orchestration/engine.py", old, new)
repl(
    "src/mimicus/orchestration/engine.py",
    "                candidate = replace(candidate, fingerprint=revised_fp, prompt_hash=identity.system_prompt_hash, tool_hash=identity.tool_manifest_hash)\n",
    "                candidate = replace(candidate, fingerprint=identity.fingerprint, prompt_hash=identity.system_prompt_hash, tool_hash=identity.tool_manifest_hash)\n",
)
# Replace one-capability audition block wholesale.
engine_text = read("src/mimicus/orchestration/engine.py")
block_start = engine_text.index("            target_cap = relevant_caps[0]")
block_end = engine_text.index("        advance(\"AUDITION_CANDIDATES\"", block_start)
replacement = '''            cap_auditions: dict[str, float] = {}
            cap_calibrations: dict[str, float] = {}
            cap_states: dict[str, str] = {}
            for target_cap in relevant_caps:
                category = canary_for.get(target_cap, "semantic_decoy")
                family = f"{target_cap}_canary"
                scoped_state_key = capability_scope(domain, target_cap, family)
                current_state = self.repository.bankruptcy_state(candidate.fingerprint, scoped_state_key)
                known_negative_lineage = self.repository.lineage_has_bankrupt_predecessor(
                    identity.lineage_id,
                    scoped_state_key,
                    exclude_fingerprint=candidate.fingerprint,
                )
                if known_negative_lineage and current_state == "ACTIVE":
                    self.repository.set_bankruptcy_state(
                        candidate.fingerprint,
                        scoped_state_key,
                        "PROBATION",
                        "known lineage has unresolved capability bankruptcy",
                    )
                    current_state = "PROBATION"
                    ledger.append(
                        "bankruptcy_changed",
                        {
                            "fingerprint": candidate.fingerprint,
                            "domain": domain,
                            "capability": target_cap,
                            "test_family": family,
                            "state": "PROBATION",
                            "reason": "known-lineage capability whitewashing defense",
                        },
                    )
                forced_fail = candidate.fingerprint in failures or candidate.name in failures or target_cap in fail_caps
                passed_answer = "wrong" if forced_fail else expected_answer[category]
                audition_result = audition(
                    candidate.fingerprint,
                    domain,
                    category,
                    passed_answer,
                    capability=target_cap,
                    test_family=family,
                    supported=True,
                )
                assert audition_result.passed is not None
                calibration = self.calibration.record_capability_verified(
                    candidate.fingerprint,
                    domain,
                    target_cap,
                    family,
                    predicted_probability=0.8,
                    outcome=audition_result.passed,
                    canary=True,
                )
                # Domain aggregate is telemetry-only. No routing path reads it for positive authority.
                self.calibration.record_verified(
                    candidate.fingerprint,
                    domain,
                    predicted_probability=0.8,
                    outcome=audition_result.passed,
                    canary=True,
                )
                evaluated = evaluate_bankruptcy(calibration)
                recovery_requested = candidate.fingerprint in recovery or candidate.name in recovery
                if recovery_requested:
                    recovered = recover(
                        BankruptcyRecord(candidate.fingerprint, scoped_state_key, BankruptcyState(current_state), "recovery path"),
                        recovery_audition_passed=audition_result.passed,
                    )
                    next_state = recovered.state.value
                    reason = recovered.reason or "recovery audition"
                elif evaluated.state == BankruptcyState.BANKRUPT:
                    next_state = "BANKRUPT"
                    reason = evaluated.reason or "verified capability audition bankruptcy"
                else:
                    next_state = current_state
                    reason = "direct verified capability calibration"
                if next_state != current_state:
                    self.repository.set_bankruptcy_state(candidate.fingerprint, scoped_state_key, next_state, reason)
                    ledger.append(
                        "bankruptcy_changed",
                        {
                            "fingerprint": candidate.fingerprint,
                            "domain": domain,
                            "capability": target_cap,
                            "test_family": family,
                            "state": next_state,
                            "reason": reason,
                        },
                    )
                state = self.repository.bankruptcy_state(candidate.fingerprint, scoped_state_key)
                cap_auditions[target_cap] = audition_result.score
                cap_calibrations[target_cap] = calibration.trust
                cap_states[target_cap] = state
                if state == "BANKRUPT":
                    lineage_exclusions["bankrupt"].append(candidate.fingerprint)
                elif state == "PROBATION":
                    lineage_exclusions["probation"].append(candidate.fingerprint)
                ledger.append(
                    "agent_auditioned",
                    {
                        "fingerprint": candidate.fingerprint,
                        "lineage_id": identity.lineage_id,
                        "domain": domain,
                        "capability": target_cap,
                        "category": category,
                        "test_family": family,
                        "applicability": "APPLICABLE",
                        "passed": audition_result.passed,
                        "score": audition_result.score,
                        "direct_attempts": calibration.attempts,
                        "direct_brier": calibration.brier_score,
                        "routing_state": state,
                    },
                )
            # Historical domain state remains inspection-only and cannot grant authority.
            if cap_states and all(state == "BANKRUPT" for state in cap_states.values()):
                self.repository.set_bankruptcy_state(candidate.fingerprint, domain, "BANKRUPT", "all relevant capabilities bankrupt")
            elif cap_states and all(state == "ACTIVE" for state in cap_states.values()):
                self.repository.set_bankruptcy_state(candidate.fingerprint, domain, "ACTIVE", "all relevant capabilities active")
            audited.append(
                replace(
                    candidate,
                    audition_score=sum(cap_auditions.values()) / max(1, len(cap_auditions)),
                    calibration_score=sum(cap_calibrations.values()) / max(1, len(cap_calibrations)),
                    bankrupt=bool(cap_states) and all(state == "BANKRUPT" for state in cap_states.values()),
                    probation=bool(cap_states) and all(state == "PROBATION" for state in cap_states.values()),
                    capability_audition_scores=cap_auditions,
                    capability_calibration_scores=cap_calibrations,
                    capability_states=cap_states,
                )
            )
'''
write("src/mimicus/orchestration/engine.py", engine_text[:block_start] + replacement + engine_text[block_end:])
# Preflight before falsifier market.
repl(
    "src/mimicus/orchestration/engine.py",
    '''        budget = BudgetLedger(request.budget_usd)
        provider_estimate = float(fixture["agent_cost"]) if "agent_cost" in fixture else self.provider.capabilities.estimated_max_cost_per_call
        if provider_estimate is None and self.provider.capabilities.known_zero_cost:
            provider_estimate = 0.0
        projected_agent_cost = request.budget_usd if provider_estimate is None and selected else float(provider_estimate or 0.0) * len(selected)
''',
    '''        budget = BudgetLedger(request.budget_usd)
        provider_estimate = float(fixture["agent_cost"]) if resolved_source_mode != "runtime" and "agent_cost" in fixture else self.provider.capabilities.estimated_max_cost_per_call
        if provider_estimate is None and self.provider.capabilities.known_zero_cost:
            provider_estimate = 0.0
        planned_members = [member.fingerprint for member in selected]
        pricing_preflight: dict[str, Any] = {
            "status": "READY",
            "planned_paid_calls": len(selected),
            "estimated_max_cost_per_call": provider_estimate,
            "configured_budget_usd": request.budget_usd,
            "planned_members": planned_members,
        }
        if selected and not self.provider.capabilities.known_zero_cost:
            if provider_estimate is None and len(selected) > 1:
                pricing_preflight.update({"status": "PRICING_PREFLIGHT_REQUIRED", "reason": "pricing_preflight_required", "executed_members": []})
                ledger.append("pricing_preflight_required", pricing_preflight)
                selected = []
                rationale["pricing_preflight"] = pricing_preflight
            elif provider_estimate is not None and provider_estimate > 0.0:
                affordable = int((request.budget_usd + 1e-12) // provider_estimate)
                if affordable < len(selected):
                    selected = selected[: max(0, affordable)]
                    pricing_preflight.update(
                        {
                            "status": "DEGRADED_BEFORE_EXECUTION" if selected else "INSUFFICIENT_BUDGET",
                            "reason": "insufficient_preflight_budget",
                            "executed_members": [member.fingerprint for member in selected],
                        }
                    )
                    ledger.append("pricing_preflight_degraded", pricing_preflight)
                    rationale["pricing_preflight"] = pricing_preflight
        pricing_preflight.setdefault("executed_members", [member.fingerprint for member in selected])
        projected_agent_cost = request.budget_usd if provider_estimate is None and selected else float(provider_estimate or 0.0) * len(selected)
''',
)
# Base evidence now canonical bundle; missing-evidence ledger.
repl(
    "src/mimicus/orchestration/engine.py",
    '''        base_evidence = fixture_evidence(fixture, domain=domain, scenario=scenario)
        base_evidence_rows = [evidence_row(item, run_id=run_id) for item in base_evidence]
        base_evidence_hashes = [str(row["evidence_hash"]) for row in base_evidence_rows]
''',
    '''        base_evidence_rows = evidence_bundle.persisted_rows()
        base_evidence_hashes = list(evidence_bundle.hashes)
        if selected_specs and not base_evidence_rows:
            ledger.append(
                "evidence_missing",
                {
                    "reason": "evidence_required_falsifier_has_no_structured_evidence",
                    "source_mode": resolved_source_mode,
                    "falsifier_primitives": [spec.primitive for spec in selected_specs],
                },
            )
''',
)
# ProviderRequest with evidence.
repl(
    "src/mimicus/orchestration/engine.py",
    "                provider_request = ProviderRequest(request.task, domain, member.name, sealed_context_id, fixture, tuple(injected_by_agent.get(member.fingerprint, [])))\n",
    "                provider_request = ProviderRequest(request.task, domain, member.name, sealed_context_id, fixture, tuple(injected_by_agent.get(member.fingerprint, [])), evidence_bundle.provider_payload())\n",
)
# Generic evidence-ref filtering rather than auto-attach.
repl(
    "src/mimicus/orchestration/engine.py",
    '''                claim_with_evidence = response.claim.model_copy(update={"evidence_refs": list(base_evidence_hashes)})
                claims_by_fp[member.fingerprint] = claim_with_evidence
                claim_trace_ids[member.fingerprint] = response.trace_id
                provider_usages.append({"fingerprint": member.fingerprint, "trace_id": response.trace_id, "usage": response.usage, "budget": reconciliation})
''',
    '''                claimed_refs = list(dict.fromkeys(response.claim.evidence_refs))
                allowed_refs = set(base_evidence_hashes)
                validated_refs = [ref for ref in claimed_refs if ref in allowed_refs]
                rejected_refs = [ref for ref in claimed_refs if ref not in allowed_refs]
                claim_with_evidence = response.claim.model_copy(update={"evidence_refs": validated_refs})
                claims_by_fp[member.fingerprint] = claim_with_evidence
                claim_trace_ids[member.fingerprint] = response.trace_id
                provider_usage = dict(response.usage)
                provider_usage.update(
                    {
                        "evidence_items_supplied": len(base_evidence_hashes),
                        "evidence_hashes_supplied": sorted(base_evidence_hashes),
                        "evidence_refs_claimed": claimed_refs,
                        "evidence_refs_validated": validated_refs,
                        "evidence_refs_rejected": rejected_refs,
                    }
                )
                provider_usages.append({"fingerprint": member.fingerprint, "trace_id": response.trace_id, "usage": provider_usage, "budget": reconciliation})
                if rejected_refs:
                    ledger.append("evidence_ref_rejected", {"fingerprint": member.fingerprint, "rejected_refs": rejected_refs, "allowed_refs": sorted(allowed_refs)})
''',
)
repl(
    "src/mimicus/orchestration/engine.py",
    '                        "verified_memory_ids": [item["memory_id"] for item in injected_by_agent.get(member.fingerprint, [])],\n',
    '                        "verified_memory_ids": [item["memory_id"] for item in injected_by_agent.get(member.fingerprint, [])],\n                        "evidence_refs": list(claim_with_evidence.evidence_refs),\n                        "evidence_hashes_supplied": sorted(base_evidence_hashes),\n',
)
# Falsifiers consume only canonical explicit evidence facts.
repl("src/mimicus/orchestration/engine.py", "                    execution = self.services.falsifiers.run(spec, fixture)\n", "                    execution = self.services.falsifiers.run(spec, falsifier_context)\n")
# Capability-scoped communication reliability.
repl(
    "src/mimicus/orchestration/engine.py",
    '''                            candidates_for_edges.append(
                                CommunicationCandidate(
                                    challenger=left_fp,
                                    target=right_fp,
                                    residual_disagreement=disagreement,
                                    verified_reliability=self.calibration.direct_trust(left_fp, domain),
''',
    '''                            relevant_edge_caps = [
                                cap
                                for cap in profile.required_capabilities
                                if cap in left_member.capabilities and left_member.capability_states.get(cap, "ACTIVE") == "ACTIVE"
                            ]
                            edge_reliability = min(
                                (
                                    self.calibration.direct_trust(left_fp, domain, cap, f"{cap}_canary")
                                    for cap in relevant_edge_caps
                                ),
                                default=0.5,
                            )
                            candidates_for_edges.append(
                                CommunicationCandidate(
                                    challenger=left_fp,
                                    target=right_fp,
                                    residual_disagreement=disagreement,
                                    verified_reliability=edge_reliability,
''',
)
# Do not mutate original claims with deterministic falsifier evidence.
repl(
    "src/mimicus/orchestration/engine.py",
    '''        decisive_evidence_hashes = [str(row["evidence_hash"]) for row in execution_evidence_rows]
        if decisive_evidence_hashes:
            for claim in ordered_claims:
                claim.evidence_refs = sorted(set(claim.evidence_refs + decisive_evidence_hashes))
''',
    '''        decisive_evidence_hashes = [str(row["evidence_hash"]) for row in execution_evidence_rows]
''',
)
# Evidence provenance source mode + preflight + separation.
repl(
    "src/mimicus/orchestration/engine.py",
    '''                "scenario": scenario,
                "fixture_hash": sha256_obj(fixture),
                "source_clusters": fixture.get("clusters", []),
                "pinned_registry_hash": fixture.get("registry_snapshot_hash"),
''',
    '''                "scenario": scenario,
                "source_mode": resolved_source_mode,
                "fixture_hash": sha256_obj(fixture) if resolved_source_mode != "runtime" else None,
                "source_clusters": falsifier_context.get("clusters", []),
                "pinned_registry_hash": falsifier_context.get("registry_snapshot_hash"),
                "provider_input_evidence_hashes": sorted(base_evidence_hashes),
                "falsifier_execution_evidence_hashes": sorted(decisive_evidence_hashes),
                "pricing_preflight": pricing_preflight,
''',
)
# Deduplicate exclusions for stable output.
repl(
    "src/mimicus/orchestration/engine.py",
    '            lineage_exclusions={key: sorted(value) for key, value in lineage_exclusions.items()},\n',
    '            lineage_exclusions={key: sorted(set(value)) for key, value in lineage_exclusions.items()},\n',
)

# ---------------------------------------------------------------------------
# MCP contract: bounded structured evidence, no fixture/source-mode knobs.
# ---------------------------------------------------------------------------
repl("src/mimicus/interfaces/mcp_server.py", '        version="0.2.0",', '        version="0.2.2",')
repl(
    "src/mimicus/interfaces/mcp_server.py",
    "        domain: str | None = None,\n        budget_usd: float = 0.0,\n",
    "        domain: str | None = None,\n        evidence: list[dict[str, Any]] | None = None,\n        budget_usd: float = 0.0,\n",
)
repl(
    "src/mimicus/interfaces/mcp_server.py",
    "            domain=domain,\n            budget_usd=budget_usd,\n",
    "            domain=domain,\n            evidence=evidence or [],\n            budget_usd=budget_usd,\n",
)

# CLI doctor exposes actual tool/evidence/pricing/preflight truth.
repl(
    "src/mimicus/interfaces/cli.py",
    "from mimicus.orchestration.engine import MiMicusEngine, RunRequest, _spec_keys, scenario_fixture\n",
    "from mimicus.orchestration.engine import MiMicusEngine, RunRequest, _spec_keys, scenario_fixture\nfrom mimicus.providers.base import Provider\n",
)
repl(
    "src/mimicus/interfaces/cli.py",
    "    services = kernel.services.snapshot()\n    placeholders = [capability for capability in services if type(kernel.services.get(capability)) is object]\n    kernel.unmount_all()\n",
    "    services = kernel.services.snapshot()\n    placeholders = [capability for capability in services if type(kernel.services.get(capability)) is object]\n    provider = kernel.services.get(\"model_provider\")\n    if not isinstance(provider, Provider):\n        raise RuntimeError(\"model provider service has invalid type\")\n    provider_caps = provider.capabilities\n    kernel.unmount_all()\n",
)
repl(
    "src/mimicus/interfaces/cli.py",
    '        "provider_live_credential_present": bool(os.getenv("OPENAI_API_KEY")) if profile == "openai" else False,\n',
    '''        "provider_live_credential_present": bool(os.getenv("OPENAI_API_KEY")) if profile == "openai" else False,
        "provider_supports_tools": provider_caps.supports_tools,
        "provider_tool_manifest_hash": provider_caps.tool_manifest_hash,
        "evidence_acquisition_available": provider_caps.evidence_acquisition_available,
        "pricing_metadata_authoritative": provider_caps.pricing_metadata_authoritative,
        "estimated_max_cost_per_call": provider_caps.estimated_max_cost_per_call,
        "pricing_preflight_status": "READY" if provider_caps.known_zero_cost or provider_caps.estimated_max_cost_per_call is not None else "REQUIRED_FOR_MULTI_CALL",
''',
)
# Plan must not infer fixture facts; scenario only classifies.
# Current scenario_fixture is safe after replacement, so no further CLI change.

# ---------------------------------------------------------------------------
# Benchmark architecture E uses explicit benchmark evidence lane.
# ---------------------------------------------------------------------------
repl(
    "src/mimicus/benchmark.py",
    '''            scenario=fixture.scenario,
            fixture=fixture.public_context,
            budget_usd=0.02,
''',
    '''            scenario=fixture.scenario,
            fixture=fixture.public_context,
            source_mode="benchmark",
            budget_usd=0.02,
''',
)

# ---------------------------------------------------------------------------
# Historical regressions: make old synthetic fixture expectations explicit.
# ---------------------------------------------------------------------------
worker = read("src/mimicus/validation/worker.py")
worker = worker.replace(
    'RunRequest(task="K3 TAM 12x mismatch", domain="finance", learn=True)',
    'RunRequest(task="K3 TAM 12x mismatch", domain="finance", scenario="tam_12x", fixture={"claim_statement": "TAM", "claim_type": "numeric", "price": 10.0, "users": 100.0, "price_period": "monthly", "claimed": 1000.0}, learn=True)',
    1,
)
worker = worker.replace(
    'RunRequest(task="source echo same origin citation", domain="research")',
    'RunRequest(task="source echo same origin citation", domain="research", scenario="echo_chamber", fixture={"claim_statement": "sources", "claim_type": "factual", "clusters": ["origin-wire", "origin-wire"], "texts": ["same report", "same report"]})',
    1,
)
worker = worker.replace(
    'RunRequest(task="freshness stale current date evidence", domain="research")',
    'RunRequest(task="freshness stale current date evidence", domain="research", scenario="freshness", fixture={"claim_statement": "freshness", "claim_type": "temporal", "evidence_date": "2025-01-01T00:00:00+00:00", "as_of": "2026-08-17T00:00:00+00:00"})',
    1,
)
worker = worker.replace(
    'RunRequest(task="citation figure entailment mismatch", domain="research")',
    'RunRequest(task="citation figure entailment mismatch", domain="research", scenario="citation_entailment", fixture={"claim_statement": "figure", "claim_type": "numeric", "claim_figure": 42, "evidence_spans": [{"span_id": "e1", "supported_figures": [41], "material_support": True}]})',
    1,
)
worker = worker.replace(
    'RunRequest(task="absence counterexample none exist", domain="research")',
    'RunRequest(task="absence counterexample none exist", domain="research", scenario="counterexample", fixture={"claim_statement": "absence", "claim_type": "factual", "absence_key": "target", "registry": {"target": {"id": "known"}}, "registry_snapshot_hash": "b" * 64})',
    1,
)
write("src/mimicus/validation/worker.py", worker)

order3 = read("src/mimicus/validation/order003_worker.py")
explicit_numeric = 'RunRequest(task="K3 TAM 12x mismatch", domain="finance", scenario="tam_12x", fixture={"claim_statement": "TAM", "claim_type": "numeric", "price": 10.0, "users": 100.0, "price_period": "monthly", "claimed": 1000.0}'
order3 = order3.replace('RunRequest(task="K3 TAM 12x mismatch", domain="finance", learn=True)', explicit_numeric + ', learn=True)', 1)
order3 = order3.replace('RunRequest(task="K3 TAM 12x mismatch", domain="finance")', explicit_numeric + ')', 1)
write("src/mimicus/validation/order003_worker.py", order3)

print("ORDER005_PATCH=APPLIED")
