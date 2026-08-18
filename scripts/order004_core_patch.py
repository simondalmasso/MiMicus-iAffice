from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"anchor missing in {path}: {old[:120]!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


# Repository identity manifest and evidence retrieval.
replace_once(
    "src/mimicus/storage/repository.py",
    '                    "tool_policy_hash": identity.tool_policy_hash,\n                    "parent_fingerprint": identity.parent_fingerprint,',
    '                    "tool_policy_hash": identity.tool_policy_hash,\n                    "runtime_model_version": identity.runtime_model_version,\n                    "phenotype_version": identity.phenotype_version,\n                    "system_prompt_hash": identity.system_prompt_hash,\n                    "tool_manifest_hash": identity.tool_manifest_hash,\n                    "policy_hash": identity.policy_hash,\n                    "provider_adapter_version": identity.provider_adapter_version,\n                    "parent_fingerprint": identity.parent_fingerprint,',
)
replace_once(
    "src/mimicus/storage/repository.py",
    '    def inspect_state(self, run_id: str | None = None) -> dict[str, Any]:\n',
    '''    def get_evidence(self, run_id: str) -> list[dict[str, Any]]:\n        with self.engine.connect() as connection:\n            rows = connection.execute(select(EvidenceRow.payload_json).where(EvidenceRow.run_id == run_id).order_by(EvidenceRow.evidence_hash)).scalars().all()\n        return [json.loads(row) for row in rows]\n\n    def resolve_evidence(self, run_id: str, evidence_hashes: list[str]) -> dict[str, dict[str, Any]]:\n        wanted = set(evidence_hashes)\n        return {str(row.get("evidence_hash")): row for row in self.get_evidence(run_id) if str(row.get("evidence_hash")) in wanted}\n\n    def inspect_state(self, run_id: str | None = None) -> dict[str, Any]:\n''',
)
replace_once(
    "src/mimicus/storage/repository.py",
    '            communications: list[str] = []\n            if run_id is not None:\n                communication_rows = connection.execute(select(CommunicationRow.payload_json).where(CommunicationRow.run_id == run_id)).scalars().all()\n                communications = [str(row) for row in communication_rows if row is not None]\n',
    '            communications: list[str] = []\n            evidence_rows: list[str] = []\n            if run_id is not None:\n                communication_rows = connection.execute(select(CommunicationRow.payload_json).where(CommunicationRow.run_id == run_id)).scalars().all()\n                communications = [str(row) for row in communication_rows if row is not None]\n                raw_evidence = connection.execute(select(EvidenceRow.payload_json).where(EvidenceRow.run_id == run_id)).scalars().all()\n                evidence_rows = [str(row) for row in raw_evidence if row is not None]\n',
)
replace_once(
    "src/mimicus/storage/repository.py",
    '            "communications": [json.loads(row) for row in communications if row],\n',
    '            "communications": [json.loads(row) for row in communications if row],\n            "evidence": [json.loads(row) for row in evidence_rows if row],\n',
)

# Engine imports.
replace_once(
    "src/mimicus/orchestration/engine.py",
    'from mimicus.agents.calibration import CalibrationLedger\n',
    'from mimicus.agents.calibration import CalibrationLedger, capability_scope\n',
)
replace_once(
    "src/mimicus/orchestration/engine.py",
    'from mimicus.claims.models import Claim\n',
    'from mimicus.claims.evidence import evidence_row, execution_evidence, fixture_evidence\nfrom mimicus.claims.models import Claim\n',
)
replace_once(
    "src/mimicus/orchestration/engine.py",
    'from mimicus.orchestration.communication import ChallengeRequest, CommunicationCandidate\n',
    'from mimicus.orchestration.budget import BudgetLedger\nfrom mimicus.orchestration.communication import ChallengeRequest, CommunicationCandidate\n',
)

# Capability-safe auditions.
start = '        candidates = self.services.agent_factory.candidates()\n'
end = '        advance("AUDITION_CANDIDATES", 0.70)\n'
engine_path = Path("src/mimicus/orchestration/engine.py")
engine = engine_path.read_text(encoding="utf-8")
left = engine.index(start)
right = engine.index(end, left) + len(end)
audition_block = '''        candidates = self.services.agent_factory.candidates()\n        audited: list[AgentCandidate] = []\n        lineage_exclusions: dict[str, list[str]] = {"bankrupt": [], "probation": []}\n        canary_for = {\n            "numeric": "parameter_trap",\n            "freshness": "temporal_decoy",\n            "independence": "semantic_decoy",\n            "entailment": "granularity_trap",\n            "counterexample": "prerequisite_blindness",\n            "synthesize": "capability_mirage",\n            "source": "semantic_decoy",\n        }\n        expected_answer = {\n            "parameter_trap": "parameter",\n            "temporal_decoy": "fresh",\n            "semantic_decoy": "relevant",\n            "granularity_trap": "granular",\n            "prerequisite_blindness": "missing",\n            "capability_mirage": "reject",\n        }\n        failures = {str(value) for value in fixture.get("audition_fail_fingerprints", [])} | {str(value) for value in fixture.get("audition_fail_names", [])}\n        fail_caps = {str(value) for value in fixture.get("audition_fail_capabilities", [])}\n        recovery = {str(value) for value in fixture.get("recovery_fingerprints", [])} | {str(value) for value in fixture.get("recovery_names", [])}\n        revisions = fixture.get("identity_revisions", {})\n        for base_candidate in candidates:\n            candidate = base_candidate\n            identity = self.services.agent_factory.identity_for(candidate)\n            if isinstance(revisions, dict) and isinstance(revisions.get(candidate.name), dict):\n                revision = revisions[candidate.name]\n                revised_fp = str(revision.get("fingerprint") or _fingerprint(candidate.name, candidate.provider, candidate.model, prompt=str(revision.get("prompt_revision", "revision"))))\n                identity = make_identity(\n                    fingerprint=revised_fp,\n                    provider=candidate.provider,\n                    model_family=candidate.model,\n                    phenotype=candidate.name,\n                    tool_policy_hash=candidate.tool_hash,\n                    runtime_model_version=candidate.runtime_model_version,\n                    phenotype_version=candidate.phenotype_version,\n                    system_prompt_hash=str(revision.get("system_prompt_hash") or candidate.prompt_hash),\n                    tool_manifest_hash=str(revision.get("tool_manifest_hash") or candidate.tool_hash),\n                    policy_hash=candidate.policy_hash,\n                    provider_adapter_version=candidate.provider_adapter_version,\n                    parent_fingerprint=str(revision.get("parent_fingerprint")) if revision.get("parent_fingerprint") else None,\n                    declared_lineage_id=str(revision.get("lineage_id")) if revision.get("lineage_id") else identity.lineage_id,\n                    revision_provenance=str(revision.get("provenance", "declared ORDER-004 revision")),\n                )\n                candidate = replace(candidate, fingerprint=revised_fp, prompt_hash=identity.system_prompt_hash, tool_hash=identity.tool_manifest_hash)\n            self.repository.register_identity(identity)\n            candidate = replace(candidate, lineage_id=identity.lineage_id)\n            relevant_caps = [cap for cap in profile.required_capabilities if cap in candidate.capabilities]\n            if not relevant_caps:\n                ledger.append(\n                    "agent_auditioned",\n                    {\n                        "fingerprint": candidate.fingerprint,\n                        "lineage_id": identity.lineage_id,\n                        "domain": domain,\n                        "capability": None,\n                        "test_family": None,\n                        "applicability": "NOT_APPLICABLE",\n                        "passed": None,\n                        "score": 0.5,\n                        "routing_state": "ACTIVE",\n                    },\n                )\n                audited.append(replace(candidate, audition_score=0.5, calibration_score=0.5))\n                continue\n\n            target_cap = relevant_caps[0]\n            category = canary_for.get(target_cap, "semantic_decoy")\n            family = f"{target_cap}_canary"\n            scoped_state_key = capability_scope(domain, target_cap, family)\n            current_state = self.repository.bankruptcy_state(candidate.fingerprint, scoped_state_key)\n            known_negative_lineage = self.repository.lineage_has_bankrupt_predecessor(identity.lineage_id, domain, exclude_fingerprint=candidate.fingerprint)\n            if known_negative_lineage and current_state == "ACTIVE":\n                self.repository.set_bankruptcy_state(candidate.fingerprint, scoped_state_key, "PROBATION", "known lineage has unresolved domain bankruptcy")\n                current_state = "PROBATION"\n                ledger.append("bankruptcy_changed", {"fingerprint": candidate.fingerprint, "domain": domain, "capability": target_cap, "state": "PROBATION", "reason": "known-lineage whitewashing defense"})\n            forced_fail = candidate.fingerprint in failures or candidate.name in failures or target_cap in fail_caps\n            passed_answer = "wrong" if forced_fail else expected_answer[category]\n            audition_result = audition(candidate.fingerprint, domain, category, passed_answer, capability=target_cap, test_family=family, supported=True)\n            assert audition_result.passed is not None\n            calibration = self.calibration.record_capability_verified(candidate.fingerprint, domain, target_cap, family, predicted_probability=0.8, outcome=audition_result.passed, canary=True)\n            # Keep the historical domain summary for ORDER-003 compatibility, but routing decisions below are capability-scoped.\n            self.calibration.record_verified(candidate.fingerprint, domain, predicted_probability=0.8, outcome=audition_result.passed, canary=True)\n            evaluated = evaluate_bankruptcy(calibration)\n            recovery_requested = candidate.fingerprint in recovery or candidate.name in recovery\n            if recovery_requested:\n                recovered = recover(BankruptcyRecord(candidate.fingerprint, scoped_state_key, BankruptcyState(current_state), "recovery path"), recovery_audition_passed=audition_result.passed)\n                next_state = recovered.state.value\n                reason = recovered.reason or "recovery audition"\n            elif evaluated.state == BankruptcyState.BANKRUPT:\n                next_state = "BANKRUPT"\n                reason = evaluated.reason or "verified capability audition bankruptcy"\n            else:\n                next_state = current_state\n                reason = "direct verified capability calibration"\n            if next_state != current_state:\n                self.repository.set_bankruptcy_state(candidate.fingerprint, scoped_state_key, next_state, reason)\n                ledger.append("bankruptcy_changed", {"fingerprint": candidate.fingerprint, "domain": domain, "capability": target_cap, "test_family": family, "state": next_state, "reason": reason})\n            if next_state == "BANKRUPT":\n                self.repository.set_bankruptcy_state(candidate.fingerprint, domain, "BANKRUPT", f"capability {target_cap}: {reason}")\n            elif recovery_requested and next_state == "ACTIVE":\n                self.repository.set_bankruptcy_state(candidate.fingerprint, domain, "ACTIVE", f"capability {target_cap} recovery audition passed")\n            state = self.repository.bankruptcy_state(candidate.fingerprint, scoped_state_key)\n            if state == "BANKRUPT":\n                lineage_exclusions["bankrupt"].append(candidate.fingerprint)\n            elif state == "PROBATION":\n                lineage_exclusions["probation"].append(candidate.fingerprint)\n            ledger.append(\n                "agent_auditioned",\n                {\n                    "fingerprint": candidate.fingerprint,\n                    "lineage_id": identity.lineage_id,\n                    "domain": domain,\n                    "capability": target_cap,\n                    "category": category,\n                    "test_family": family,\n                    "applicability": "APPLICABLE",\n                    "passed": audition_result.passed,\n                    "score": audition_result.score,\n                    "direct_attempts": calibration.attempts,\n                    "direct_brier": calibration.brier_score,\n                    "routing_state": state,\n                },\n            )\n            audited.append(replace(candidate, audition_score=audition_result.score, calibration_score=calibration.trust, bankrupt=state == "BANKRUPT", probation=state == "PROBATION"))\n        advance("AUDITION_CANDIDATES", 0.70)\n'''
engine = engine[:left] + audition_block + engine[right:]
engine_path.write_text(engine, encoding="utf-8")

# Budget-aware market and evidence pre-normalization.
replace_once(
    "src/mimicus/orchestration/engine.py",
    '        max_tests = {"fast": 1, "normal": 3, "deep": 5}[request.depth]\n        selected_specs, scores = FalsifierMarket().select(candidate_specs, budget_usd=request.budget_usd, max_tests=max_tests, information_floor=0.05)\n        ledger.append("falsifier_market_scored", {"scores": [asdict(score) for score in scores], "budget_usd": request.budget_usd, "max_tests": max_tests})\n',
    '''        budget = BudgetLedger(request.budget_usd)\n        provider_estimate = float(fixture["agent_cost"]) if "agent_cost" in fixture else self.provider.capabilities.estimated_max_cost_per_call\n        if provider_estimate is None and self.provider.capabilities.known_zero_cost:\n            provider_estimate = 0.0\n        projected_agent_cost = request.budget_usd if provider_estimate is None and selected else float(provider_estimate or 0.0) * len(selected)\n        market_budget = max(0.0, request.budget_usd - min(request.budget_usd, projected_agent_cost))\n        max_tests = {"fast": 1, "normal": 3, "deep": 5}[request.depth]\n        selected_specs, scores = FalsifierMarket().select(candidate_specs, budget_usd=market_budget, max_tests=max_tests, information_floor=0.05)\n        ledger.append("falsifier_market_scored", {"scores": [asdict(score) for score in scores], "budget_usd": market_budget, "hard_cap_usd": request.budget_usd, "max_tests": max_tests})\n''',
)
replace_once(
    "src/mimicus/orchestration/engine.py",
    '        claims_by_fp: dict[str, Claim] = {}\n        claim_trace_ids: dict[str, str | None] = {}\n        executions: list[FalsifierExecution] = []\n        communications: list[dict[str, Any]] = []\n        provider_call_count = 0\n        reserved_cost = 0.0\n        budget_lock = asyncio.Lock()\n        communication_stagnated = False\n\n        async def reserve(cost: float) -> bool:\n            nonlocal reserved_cost\n            async with budget_lock:\n                if reserved_cost + cost > request.budget_usd + 1e-12:\n                    return False\n                reserved_cost += cost\n                return True\n',
    '''        base_evidence = fixture_evidence(fixture, domain=domain, scenario=scenario)\n        base_evidence_rows = [evidence_row(item) for item in base_evidence]\n        base_evidence_hashes = [str(row["evidence_hash"]) for row in base_evidence_rows]\n        claims_by_fp: dict[str, Claim] = {}\n        claim_trace_ids: dict[str, str | None] = {}\n        provider_usages: list[dict[str, Any]] = []\n        executions: list[FalsifierExecution] = []\n        communications: list[dict[str, Any]] = []\n        provider_call_count = 0\n        communication_stagnated = False\n''',
)

# Agent work accounting and evidence refs.
replace_once(
    "src/mimicus/orchestration/engine.py",
    '''                estimated = float(fixture.get("agent_cost", 0.0))\n                if not await reserve(estimated):\n                    ledger.append("budget_exhausted", {"node_id": node.node_id, "kind": node.kind.value})\n                    return {"budget_exhausted": True}\n                sealed_context_id = str(uuid5(NAMESPACE_URL, f"{run_id}:{member.fingerprint}:sealed"))\n                provider_request = ProviderRequest(\n                    request.task,\n                    domain,\n                    member.name,\n                    sealed_context_id,\n                    fixture,\n                    tuple(injected_by_agent.get(member.fingerprint, [])),\n                )\n                response: ProviderResponse = await self.provider.generate_request_async(provider_request)\n                provider_call_count += 1\n                claims_by_fp[member.fingerprint] = response.claim\n                claim_trace_ids[member.fingerprint] = response.trace_id\n''',
    '''                estimated = float(fixture["agent_cost"]) if "agent_cost" in fixture else self.provider.capabilities.estimated_max_cost_per_call\n                reservation = await budget.reserve("agent_generation", estimated, known_zero_cost=self.provider.capabilities.known_zero_cost)\n                if reservation is None:\n                    ledger.append("budget_exhausted", {"node_id": node.node_id, "kind": node.kind.value, "category": "agent_generation"})\n                    return {"budget_exhausted": True}\n                sealed_context_id = str(uuid5(NAMESPACE_URL, f"{run_id}:{member.fingerprint}:sealed"))\n                provider_request = ProviderRequest(request.task, domain, member.name, sealed_context_id, fixture, tuple(injected_by_agent.get(member.fingerprint, [])))\n                try:\n                    response: ProviderResponse = await self.provider.generate_request_async(provider_request)\n                except asyncio.CancelledError:\n                    await budget.release(reservation, reason="agent task cancelled")\n                    ledger.append("dag_node_cancelled", {"node_id": node.node_id, "kind": node.kind.value, "reservation_released": True})\n                    raise\n                except BaseException:\n                    await budget.release(reservation, reason="agent task failed before provider result")\n                    ledger.append("dag_node_failed", {"node_id": node.node_id, "kind": node.kind.value, "reservation_released": True})\n                    raise\n                reconciliation = await budget.reconcile(reservation, response.cost)\n                provider_call_count += 1\n                claim_with_evidence = response.claim.model_copy(update={"evidence_refs": sorted(set(response.claim.evidence_refs + base_evidence_hashes))})\n                claims_by_fp[member.fingerprint] = claim_with_evidence\n                claim_trace_ids[member.fingerprint] = response.trace_id\n                provider_usages.append({"fingerprint": member.fingerprint, "trace_id": response.trace_id, "usage": response.usage, "budget": reconciliation})\n''',
)
replace_once(
    "src/mimicus/orchestration/engine.py",
    '                        "claim_hash": response.claim.hash,\n',
    '                        "claim_hash": claim_with_evidence.hash,\n',
)
replace_once(
    "src/mimicus/orchestration/engine.py",
    '                        "probability": response.claim.probability,\n',
    '                        "probability": claim_with_evidence.probability,\n',
)
replace_once(
    "src/mimicus/orchestration/engine.py",
    '                    "claim": response.claim.model_dump(mode="json"),\n',
    '                    "claim": claim_with_evidence.model_dump(mode="json"),\n',
)

# Falsifier budget accounting.
replace_once(
    "src/mimicus/orchestration/engine.py",
    '''                spec = specs_by_hash[node.identity]\n                if not self.services.sandbox.permits(spec.primitive):\n                    raise RuntimeError(f"sandbox rejected primitive {spec.primitive}")\n                execution = self.services.falsifiers.run(spec, fixture)\n                executions.append(execution)\n''',
    '''                spec = specs_by_hash[node.identity]\n                if not self.services.sandbox.permits(spec.primitive):\n                    raise RuntimeError(f"sandbox rejected primitive {spec.primitive}")\n                reservation = await budget.reserve("falsifier", spec.estimated_cost, known_zero_cost=spec.estimated_cost == 0.0)\n                if reservation is None:\n                    ledger.append("budget_exhausted", {"node_id": node.node_id, "kind": node.kind.value, "category": "falsifier"})\n                    return {"budget_exhausted": True}\n                try:\n                    execution = self.services.falsifiers.run(spec, fixture)\n                except BaseException:\n                    await budget.release(reservation, reason="falsifier failed")\n                    raise\n                await budget.reconcile(reservation, execution.cost)\n                executions.append(execution)\n''',
)

# Challenge budget accounting.
replace_once(
    "src/mimicus/orchestration/engine.py",
    '                                    expected_information_gain=max(0.2, disagreement),\n                                )\n',
    '                                    expected_information_gain=max(0.2, disagreement),\n                                    estimated_cost=float(fixture["challenge_cost"]) if "challenge_cost" in fixture else float(self.provider.capabilities.estimated_max_cost_per_call or 0.0),\n                                )\n',
)
replace_once(
    "src/mimicus/orchestration/engine.py",
    '''                        challenge_response = await self.provider.challenge_async(challenge_request)\n                        provider_call_count += 1\n''',
    '''                        challenge_estimate = float(fixture["challenge_cost"]) if "challenge_cost" in fixture else self.provider.capabilities.estimated_max_cost_per_call\n                        reservation = await budget.reserve("challenge", challenge_estimate, known_zero_cost=self.provider.capabilities.known_zero_cost)\n                        if reservation is None:\n                            ledger.append("budget_exhausted", {"node_id": node.node_id, "kind": node.kind.value, "category": "challenge", "round": round_no})\n                            continue\n                        try:\n                            challenge_response = await self.provider.challenge_async(challenge_request)\n                        except asyncio.CancelledError:\n                            await budget.release(reservation, reason="challenge cancelled")\n                            raise\n                        except BaseException:\n                            await budget.release(reservation, reason="challenge failed")\n                            raise\n                        await budget.reconcile(reservation, challenge_response.cost)\n                        provider_call_count += 1\n''',
)

# Final evidence and truthful budget snapshot.
replace_once(
    "src/mimicus/orchestration/engine.py",
    '        result = RunResult(\n',
    '        all_evidence_rows = base_evidence_rows + [evidence_row(execution_evidence(item)) for item in ordered_executions]\n        budget_snapshot = budget.snapshot()\n        budget_snapshot.update({"latency_ms": sum(execution.latency_ms for execution in ordered_executions), "max_tests": max_tests, "max_concurrency": request.max_concurrency})\n        result = RunResult(\n',
)
old_budget = '''            budget={\n                "limit_usd": request.budget_usd,\n                "reserved_usd": reserved_cost,\n                "spent_usd": sum(execution.cost for execution in ordered_executions) + float(fixture.get("agent_cost", 0.0)) * len(ordered_claims),\n                "latency_ms": sum(execution.latency_ms for execution in ordered_executions),\n                "max_tests": max_tests,\n                "max_concurrency": request.max_concurrency,\n            },\n'''
replace_once("src/mimicus/orchestration/engine.py", old_budget, '            budget=budget_snapshot,\n')
replace_once(
    "src/mimicus/orchestration/engine.py",
    '                "provider": self.provider.capabilities.__dict__,\n',
    '                "provider": self.provider.capabilities.__dict__,\n                "provider_usages": provider_usages,\n                "evidence_hashes": [row["evidence_hash"] for row in all_evidence_rows],\n',
)
replace_once("src/mimicus/orchestration/engine.py", '            evidence=[],\n', '            evidence=all_evidence_rows,\n')

print("ORDER004_CORE_PATCH=APPLIED")
