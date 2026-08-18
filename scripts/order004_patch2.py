from __future__ import annotations

from pathlib import Path


def rep(path: str, old: str, new: str, count: int = 1) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if text.count(old) < count:
        raise SystemExit(f"missing anchor in {path}: {old[:100]!r}")
    p.write_text(text.replace(old, new, count), encoding="utf-8")


# F010: separate configured runtime model identity from adapter version.
rep(
    "src/mimicus/providers/base.py",
    '    version: str = "unknown"\n    usage_metadata_available: bool = False\n',
    '    version: str = "unknown"\n    adapter_version: str = "unknown"\n    usage_metadata_available: bool = False\n',
)
rep(
    "src/mimicus/plugins/services.py",
    '                    provider_adapter_version=caps.version,\n',
    '                    provider_adapter_version=caps.adapter_version,\n',
)
rep(
    "src/mimicus/plugins/services.py",
    '            provider_adapter_version=candidate.provider_adapter_version,\n',
    '            provider_adapter_version=candidate.provider_adapter_version,\n',
)
rep(
    "src/mimicus/providers/scripted.py",
    '            version="2.1",\n            usage_metadata_available=True,\n',
    '            version="fixture-v2",\n            adapter_version="scripted-adapter-v2.1",\n            usage_metadata_available=True,\n',
)
rep(
    "src/mimicus/providers/openai_agents.py",
    '            version="0.21.1-adapter-v2.1",\n            usage_metadata_available=True,\n',
    '            version=f"configured:{self.model}",\n            adapter_version="openai-agents-0.21.1/mimicus-adapter-v2.1",\n            usage_metadata_available=True,\n',
)

# F009 compatibility: keep capability scope normative but mirror probation into legacy domain view.
rep(
    "src/mimicus/orchestration/engine.py",
    '                self.repository.set_bankruptcy_state(candidate.fingerprint, scoped_state_key, "PROBATION", "known lineage has unresolved domain bankruptcy")\n                current_state = "PROBATION"\n',
    '                self.repository.set_bankruptcy_state(candidate.fingerprint, scoped_state_key, "PROBATION", "known lineage has unresolved domain bankruptcy")\n                self.repository.set_bankruptcy_state(candidate.fingerprint, domain, "PROBATION", f"capability {target_cap}: known-lineage whitewashing defense")\n                current_state = "PROBATION"\n',
)

# F013: evidence refs are only refs that MiMicus actually persists.
rep(
    "src/mimicus/orchestration/engine.py",
    '                claim_with_evidence = response.claim.model_copy(update={"evidence_refs": sorted(set(response.claim.evidence_refs + base_evidence_hashes))})\n',
    '                claim_with_evidence = response.claim.model_copy(update={"evidence_refs": list(base_evidence_hashes)})\n',
)
rep(
    "src/mimicus/claims/evidence.py",
    'def evidence_row(evidence: Evidence) -> dict[str, Any]:\n    return evidence.model_dump(mode="json") | {"evidence_hash": evidence.hash}\n',
    'def evidence_row(evidence: Evidence, *, run_id: str | None = None) -> dict[str, Any]:\n    canonical_hash = evidence.hash\n    evidence_hash = canonical_hash if run_id is None else sha256_obj({"run_id": run_id, "canonical_evidence_hash": canonical_hash})\n    return evidence.model_dump(mode="json") | {"canonical_evidence_hash": canonical_hash, "evidence_hash": evidence_hash}\n',
)
rep(
    "src/mimicus/orchestration/engine.py",
    '        base_evidence_rows = [evidence_row(item) for item in base_evidence]\n',
    '        base_evidence_rows = [evidence_row(item, run_id=run_id) for item in base_evidence]\n',
)
rep(
    "src/mimicus/orchestration/engine.py",
    '        ordered_claims = [claims_by_fp[key] for key in sorted(claims_by_fp)]\n        ordered_executions = sorted(executions, key=lambda row: row.spec_hash)\n',
    '        ordered_claims = [claims_by_fp[key] for key in sorted(claims_by_fp)]\n        ordered_executions = sorted(executions, key=lambda row: row.spec_hash)\n        execution_evidence_rows = [evidence_row(execution_evidence(item), run_id=run_id) for item in ordered_executions]\n        decisive_evidence_hashes = [str(row["evidence_hash"]) for row in execution_evidence_rows]\n        if decisive_evidence_hashes:\n            for claim in ordered_claims:\n                claim.evidence_refs = sorted(set(claim.evidence_refs + decisive_evidence_hashes))\n',
)
rep(
    "src/mimicus/orchestration/engine.py",
    '        all_evidence_rows = base_evidence_rows + [evidence_row(execution_evidence(item)) for item in ordered_executions]\n',
    '        all_evidence_rows = base_evidence_rows + execution_evidence_rows\n',
)
rep(
    "src/mimicus/orchestration/engine.py",
    '        return result | {"replay_state": replay, "events": events, "persistent_state": self.repository.inspect_state(run_id)}\n',
    '        evidence = self.repository.get_evidence(run_id)\n        return result | {"replay_state": replay, "events": events, "evidence": evidence, "persistent_state": self.repository.inspect_state(run_id)}\n',
)

# F017: benchmark provider derives from structured public evidence, never answer-bearing task tokens.
path = Path("src/mimicus/benchmark.py")
text = path.read_text(encoding="utf-8")
start = text.index("class BenchmarkProvider(Provider):")
end = text.index("\n\ndef fixture_stream", start)
provider_block = '''class BenchmarkProvider(Provider):
    """Deterministic benchmark provider using public structured evidence only."""

    def __init__(self, *, error_modulus: int = 11, force_statement: str | None = None) -> None:
        self.error_modulus = max(2, error_modulus)
        self.force_statement = force_statement
        self.calls = 0

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider_id="benchmark-scripted",
            model_id="public-structured-heuristic",
            version="benchmark-v2.1",
            adapter_version="benchmark-adapter-v2.1",
            usage_metadata_available=True,
            known_zero_cost=False,
            estimated_max_cost_per_call=0.0001,
            pricing_metadata_authoritative=True,
        )

    @staticmethod
    def _public_answer(context: dict[str, Any]) -> str:
        marker = context.get("benchmark_marker")
        if marker == 1:
            return "ALPHA"
        if marker == 2:
            return "BETA"
        checks: list[bool] = []
        if all(key in context for key in ("price", "users", "claimed")):
            multiplier = 12.0 if str(context.get("price_period", "annual")).lower() == "monthly" else 1.0
            expected = float(context["price"]) * float(context["users"]) * multiplier
            claimed = float(context["claimed"])
            checks.append(abs(expected - claimed) / max(abs(expected), 1e-9) <= 0.01)
        if "evidence_date" in context and "as_of" in context:
            from datetime import datetime

            observed = datetime.fromisoformat(str(context["evidence_date"]).replace("Z", "+00:00"))
            as_of = datetime.fromisoformat(str(context["as_of"]).replace("Z", "+00:00"))
            checks.append((as_of - observed).days <= 90)
        clusters = context.get("clusters")
        if isinstance(clusters, list) and clusters:
            checks.append(len(set(str(value) for value in clusters)) >= 2)
        if "claim_figure" in context and isinstance(context.get("evidence_spans"), list):
            figure = context["claim_figure"]
            spans = cast(list[dict[str, Any]], context["evidence_spans"])
            checks.append(any(bool(span.get("material_support")) and figure in list(span.get("supported_figures", [])) for span in spans))
        if "absence_key" in context and isinstance(context.get("registry"), dict):
            checks.append(str(context["absence_key"]) not in cast(dict[str, Any], context["registry"]))
        if not checks:
            return "INCONCLUSIVE"
        return "SUPPORTED" if all(checks) else "FALSIFIED"

    @staticmethod
    def _flip(answer: str) -> str:
        return {"SUPPORTED": "FALSIFIED", "FALSIFIED": "SUPPORTED", "ALPHA": "BETA", "BETA": "ALPHA"}.get(answer, answer)

    async def generate_request_async(self, request: ProviderRequest) -> ProviderResponse:
        self.calls += 1
        answer = self.force_statement or self._public_answer(request.fixture)
        digest = int(sha256_obj({"public_context": request.fixture, "phenotype": request.phenotype})[:8], 16)
        if self.force_statement is None and digest % self.error_modulus == 0:
            answer = self._flip(answer)
        probability = 0.55 + (digest % 36) / 100.0
        claim = Claim(statement=answer, domain=request.domain, probability=min(0.91, probability), claim_type="factual")
        trace_id = str(uuid5(NAMESPACE_URL, f"benchmark:{sha256_obj(request.fixture)}:{request.phenotype}:{self.calls}"))
        await asyncio.sleep(0)
        return ProviderResponse(
            claim=claim,
            cost=0.0001,
            latency_ms=0.1,
            trace_id=trace_id,
            usage={"simulated": True, "monetary_cost_status": "KNOWN", "monetary_cost_usd": 0.0001},
        )

    async def challenge_async(self, request: ChallengeRequest) -> ChallengeResponse:
        self.calls += 1
        await asyncio.sleep(0)
        return ChallengeResponse(
            disposition="partial",
            revised_probability=0.58,
            revised_status=ClaimStatus.PROPOSED,
            rationale_summary="benchmark structured challenge",
            provider_call_id=str(uuid5(NAMESPACE_URL, f"benchmark-challenge:{request.hash}:{self.calls}")),
            cost=0.0001,
            usage={"simulated": True, "monetary_cost_status": "KNOWN", "monetary_cost_usd": 0.0001},
        )
'''
text = text[:start] + provider_block + text[end:]
# Imports for challenge response/status.
text = text.replace(
    "from mimicus.orchestration.engine import MiMicusEngine, RunRequest\n",
    "from mimicus.orchestration.communication import ChallengeRequest, ChallengeResponse\nfrom mimicus.orchestration.engine import MiMicusEngine, RunRequest\n",
    1,
)
text = text.replace("from mimicus.types import Verdict\n", "from mimicus.types import ClaimStatus, Verdict\n", 1)
# Neutral task wording and public marker evidence.
replacements = {
    '"task": "numeric mismatch public evidence"': '"task": "Evaluate annualized numeric consistency from structured evidence"',
    '"task": "numeric aligned public evidence"': '"task": "Evaluate annualized numeric consistency from structured evidence"',
    '"task": "freshness stale public evidence"': '"task": "Evaluate temporal validity from structured evidence"',
    '"task": "fresh-current public evidence"': '"task": "Evaluate temporal validity from structured evidence"',
    '"task": "source echo-duplicate public evidence"': '"task": "Evaluate source independence from structured provenance"',
    '"task": "independent-sources public evidence"': '"task": "Evaluate source independence from structured provenance"',
    '"task": "citation unsupported-figure public evidence"': '"task": "Evaluate citation entailment for the structured figure evidence"',
    '"task": "citation entailed-figure public evidence"': '"task": "Evaluate citation entailment for the structured figure evidence"',
    '"task": "absence counterexample-found public evidence"': '"task": "Evaluate an absence claim against the structured counterexample registry"',
    '"task": "registry-absent public evidence"': '"task": "Evaluate an absence claim against the structured counterexample registry"',
    '"task": "general-alpha public classification"': '"task": "Classify the structured public marker using the fixed rule"',
    '"task": "general-beta public classification"': '"task": "Classify the structured public marker using the fixed rule"',
    '"task": "mixed-fail source citation fresh figure echo public evidence"': '"task": "Assess fresh source citation figure and counterexample evidence"',
    '"context": {"claim_statement": "ALPHA", "claim_type": "factual"}': '"context": {"claim_statement": "classification", "claim_type": "factual", "benchmark_marker": 1}',
    '"context": {"claim_statement": "BETA", "claim_type": "factual"}': '"context": {"claim_statement": "classification", "claim_type": "factual", "benchmark_marker": 2}',
    '                "force_sparse": True,\n                "force_challenge": True,\n': '                "absence_key": "target",\n                "registry": {"target": {"id": 1}},\n                "registry_snapshot_hash": "e" * 64,\n',
    '            "keys": ("F2", "F3", "F4"),': '            "keys": ("F2", "F3", "F4", "F5"),',
    '        fixture_id = f"fx-{index:04d}-{template[\'name\']}"': '        fixture_id = f"fx-{index:04d}"',
    '            budget_usd=0.0,': '            budget_usd=0.02,',
    '            cost=float(cast(Any, result.budget.get("spent_usd", 0.0))),': '            cost=float(cast(Any, result.budget.get("known_actual_usd", result.budget.get("spent_usd", 0.0)))),',
}
for old, new in replacements.items():
    if old not in text:
        raise SystemExit(f"benchmark anchor missing: {old}")
    text = text.replace(old, new, 1)
# Anti-rigging fixture is neutral and evidence-driven.
text = text.replace('fixture_id="anti-general-alpha",\n        task="general-alpha public classification anti-rigging",', 'fixture_id="anti-neutral",\n        task="Classify the structured public marker using the fixed rule",', 1)
text = text.replace('public_context={"claim_statement": "ALPHA", "claim_type": "factual"},', 'public_context={"claim_statement": "classification", "claim_type": "factual", "benchmark_marker": 1},', 1)
# Raw rows carry actual morphology.
text = text.replace('    ledger_head: str\n\n\nclass ArchitectureRunner', '    ledger_head: str\n    morphology: str = "baseline"\n\n\nclass ArchitectureRunner', 1)
text = text.replace('                        ledger_head=output.ledger_head,\n', '                        ledger_head=output.ledger_head,\n                        morphology=str(output.trace.get("morphology", "baseline")),\n', 1)
# Leakage probe and morphology distribution.
marker = '\n\nasync def _build_report(count: int) -> tuple[dict[str, Any], list[RawRow]]:\n'
if marker not in text:
    raise SystemExit("benchmark build-report anchor missing")
probe = '''\n\nasync def leakage_probe() -> dict[str, Any]:
    fixtures = fixture_stream(40)
    forbidden = ("mismatch", "aligned", "stale", "unsupported-figure", "counterexample-found", "general-alpha", "general-beta", "mixed-fail")
    leaking = [fixture.fixture_id for fixture in fixtures if any(token in fixture.task.lower() for token in forbidden)]
    sample = fixtures[0]
    provider = BenchmarkProvider(error_modulus=10_000)
    original = await provider.generate_request_async(ProviderRequest(sample.task, sample.domain, "leakage", "original", sample.public_context))
    renamed = await provider.generate_request_async(ProviderRequest("Neutral wording replacement with identical evidence", sample.domain, "leakage", "renamed", sample.public_context))
    return {
        "task_answer_markers_absent": not leaking,
        "leaking_fixture_ids": leaking,
        "renamed_task_same_verdict": original.claim.statement == renamed.claim.statement,
        "public_context_hash": sha256_obj(sample.public_context),
        "passed": not leaking and original.claim.statement == renamed.claim.statement,
    }
'''
text = text.replace(marker, probe + marker, 1)
text = text.replace('    anti = await anti_rigging_probe()\n', '    anti = await anti_rigging_probe()\n    leakage = await leakage_probe()\n    e_rows = [row for row in rows if row.architecture == "E"]\n    morphology_distribution: dict[str, int] = {}\n    agent_count_distribution: dict[str, int] = {}\n    challenge_edge_distribution: dict[str, int] = {}\n    for row in e_rows:\n        morphology_distribution[row.morphology] = morphology_distribution.get(row.morphology, 0) + 1\n        agent_count_distribution[str(row.agent_count)] = agent_count_distribution.get(str(row.agent_count), 0) + 1\n        challenge_edge_distribution[str(row.communication_edge_count)] = challenge_edge_distribution.get(str(row.communication_edge_count), 0) + 1\n', 1)
text = text.replace('        "benchmark_version": "ORDER-003-v0.2-execution-derived",', '        "benchmark_version": "ORDER-004-v0.2.1-neutral-execution-derived",', 1)
text = text.replace('        "anti_rigging": anti,\n', '        "anti_rigging": anti,\n        "leakage_probe": leakage,\n        "morphology_distribution": {"classes": morphology_distribution, "agent_counts": agent_count_distribution, "challenge_edges": challenge_edge_distribution},\n', 1)
text = text.replace('    anti_path.write_text(json.dumps(report["anti_rigging"], indent=2, sort_keys=True) + "\\n", encoding="utf-8")\n', '    anti_path.write_text(json.dumps(report["anti_rigging"], indent=2, sort_keys=True) + "\\n", encoding="utf-8")\n    (output_json.parent / "BENCHMARK_MORPHOLOGY_DISTRIBUTION.json").write_text(json.dumps(report["morphology_distribution"], indent=2, sort_keys=True) + "\\n", encoding="utf-8")\n    (output_json.parent / "BENCHMARK_LEAKAGE.json").write_text(json.dumps(report["leakage_probe"], indent=2, sort_keys=True) + "\\n", encoding="utf-8")\n', 1)
text = text.replace("# MiMicus ORDER-003 execution-derived benchmark", "# MiMicus ORDER-004 neutral execution-derived benchmark", 1)
path.write_text(text, encoding="utf-8")

print("ORDER004_PATCH2=APPLIED")
