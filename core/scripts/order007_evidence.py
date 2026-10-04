from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from mimicus.claims.evidence_bundle import EvidenceInput
from mimicus.claims.models import Claim, NumericAssertion
from mimicus.falsifiers.market import FalsifierMarket
from mimicus.falsifiers.spec import FalsifierSpec
from mimicus.orchestration.engine import MiMicusEngine, RunRequest
from mimicus.providers.base import ProviderRequest, ProviderResponse
from mimicus.providers.scripted import ScriptedProvider
from mimicus.storage.swarm_state import SwarmStateStore
from mimicus.verification.models import VerificationSubmission


def _write(root: Path, name: str, payload: dict[str, Any]) -> None:
    (root / name).write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _evidence(facts: dict[str, Any], *, cluster: str = "order007-audit") -> list[EvidenceInput]:
    return [
        EvidenceInput(
            origin="audit://order007/runtime",
            independence_cluster=cluster,
            content="ORDER-007 runtime structured evidence",
            extracted_facts=facts,
            observed_at=datetime(2026, 8, 18, 15, tzinfo=UTC),
        )
    ]


def _numeric(claimed: float = 1248.0) -> dict[str, Any]:
    return {"price": 10.0, "users": 10.0, "price_period": "monthly", "claimed": claimed}


class RecordingProvider(ScriptedProvider):
    def __init__(self, *, same_statement: bool = False) -> None:
        super().__init__()
        self.same_statement = same_statement
        self.requests: list[dict[str, Any]] = []

    async def generate_request_async(self, request: ProviderRequest) -> ProviderResponse:
        response = await super().generate_request_async(request)
        evidence_refs = [str(row["evidence_hash"]) for row in request.evidence if isinstance(row, dict) and isinstance(row.get("evidence_hash"), str)]
        evidence_keys = sorted(
            {str(key) for row in request.evidence if isinstance(row, dict) for key in (row.get("extracted_facts", {}) if isinstance(row.get("extracted_facts"), dict) else {})}
        )
        self.requests.append(
            {
                "phenotype": request.phenotype,
                "task": request.task,
                "evidence_keys": evidence_keys,
                "evidence_hashes": evidence_refs,
            }
        )
        probabilities = {
            "numeric-1": 0.93,
            "source-1": 0.21,
            "counterexample-1": 0.67,
            "critic-1": 0.34,
            "synth-1": 0.74,
        }
        statement = "same verified proposition" if self.same_statement else f"{request.phenotype}:{request.task}"
        asserted_value = next(
            (
                row.get("extracted_facts", {}).get("claimed")
                for row in request.evidence
                if isinstance(row, dict) and isinstance(row.get("extracted_facts"), dict) and row.get("extracted_facts", {}).get("claimed") is not None
            ),
            None,
        )
        claim = Claim(
            statement=statement,
            domain=request.domain,
            probability=probabilities.get(request.phenotype, 0.6),
            claim_type="numeric",
            assertion=(NumericAssertion(asserted_value=float(asserted_value)) if isinstance(asserted_value, (int, float)) else None),
            evidence_refs=evidence_refs,
        )
        return replace(response, claim=claim)


def _receipt(
    run: Any,
    claim: dict[str, Any],
    *,
    verifier_id: str,
    token: str,
    status: str,
    cluster: str,
    snapshot_hashes: tuple[str, ...] = (),
    supersedes: str | None = None,
    observed_hour: int = 16,
) -> VerificationSubmission:
    return VerificationSubmission(
        run_id=run.run_id,
        claim_hash=str(claim["claim_hash"]),
        verified_status=status,
        authority_class="deterministic_oracle",
        evidence_hashes=tuple(run.evidence_provenance["provider_input_evidence_hashes"]),
        snapshot_hashes=snapshot_hashes,
        verifier_id=verifier_id,
        auth_token=token,
        observed_at=datetime(2026, 8, 18, observed_hour, tzinfo=UTC),
        source_independence_cluster=cluster,
        supersedes_receipt_hash=supersedes,
    )


def verifier_authority_binding(root: Path) -> dict[str, Any]:
    db = f"sqlite:///{root / 'authority.db'}"
    engine = MiMicusEngine(db)
    run = engine.run(
        RunRequest(
            task="Assess the supplied structured material.",
            domain="finance",
            evidence=_evidence(_numeric()),
            max_agents=2,
            depth="deep",
            learn=True,
        )
    )
    assert run.final_claims and run.falsifiers
    claim = run.final_claims[0]
    snapshot = str(run.falsifiers[0]["execution_snapshot_hash"])
    store = SwarmStateStore(engine.repository.engine)
    before = store.learned_state("finance")

    forged = engine.submit_verification(
        VerificationSubmission(
            run_id=run.run_id,
            claim_hash=str(claim["claim_hash"]),
            verified_status="FALSIFIED",
            authority_class="trusted_human",
            evidence_hashes=tuple(run.evidence_provenance["provider_input_evidence_hashes"]),
            snapshot_hashes=(snapshot,),
            verifier_id="human:caller-minted",
            auth_token="caller-cannot-mint-authority",
            observed_at=datetime(2026, 8, 18, 16, tzinfo=UTC),
            source_independence_cluster="caller-self-asserted",
        )
    )
    assert forged["accepted"] is False
    assert forged["receipt"]["rejection_reason"] == "verifier_not_authorized"
    assert store.learned_state("finance") == before

    token = "order007-authorized-oracle-token-v1"
    verifier_id = "oracle:order007-authority"
    cluster = "order007-authority-registry-v1"
    policy = engine.register_verifier_authority(
        verifier_id=verifier_id,
        authority_class="deterministic_oracle",
        source_independence_cluster=cluster,
        auth_token=token,
    )
    after_policy = store.learned_state("finance")
    bogus = engine.submit_verification(
        _receipt(
            run,
            claim,
            verifier_id=verifier_id,
            token=token,
            status="FALSIFIED",
            cluster=cluster,
        ).model_copy(update={"evidence_hashes": ("f" * 64,)})
    )
    assert bogus["accepted"] is False
    assert bogus["receipt"]["rejection_reason"] == "evidence_hash_not_bound_to_run"
    assert store.learned_state("finance") == after_policy

    accepted = engine.submit_verification(
        _receipt(
            run,
            claim,
            verifier_id=verifier_id,
            token=token,
            status="FALSIFIED",
            cluster=cluster,
            snapshot_hashes=(snapshot,),
        )
    )
    assert accepted["accepted"] is True
    assert accepted["attributions"]
    duplicate = engine.submit_verification(
        _receipt(
            run,
            claim,
            verifier_id=verifier_id,
            token=token,
            status="FALSIFIED",
            cluster=cluster,
            snapshot_hashes=(snapshot,),
            observed_hour=17,
        )
    )
    assert duplicate["duplicate"] is True

    superseding = engine.submit_verification(
        _receipt(
            run,
            claim,
            verifier_id=verifier_id,
            token=token,
            status="SUPPORTED",
            cluster=cluster,
            snapshot_hashes=(snapshot,),
            supersedes=str(accepted["receipt"]["receipt_hash"]),
            observed_hour=18,
        )
    )
    assert superseding["accepted"] is True
    receipts = store.receipts_for_run(run.run_id)
    old = next(row for row in receipts if row["receipt_hash"] == accepted["receipt"]["receipt_hash"])
    new = next(row for row in receipts if row["receipt_hash"] == superseding["receipt"]["receipt_hash"])
    assert old["learning_active"] is False
    assert old["superseded_by_hash"] == new["receipt_hash"]
    assert new["learning_active"] is True
    cap = str(claim["contributor_capabilities"][0])
    authority = store.verified_authority(str(claim["contributor_fingerprint"]), "finance", cap)
    assert authority["attempts"] == 1

    restarted = MiMicusEngine(db)
    restarted_store = SwarmStateStore(restarted.repository.engine)
    assert any(row["policy_hash"] == policy["policy_hash"] for row in restarted_store.verifier_policies())
    restarted_receipts = restarted_store.receipts_for_run(run.run_id)
    assert len(restarted_receipts) == 2
    payload = {
        "pass": True,
        "run_id": run.run_id,
        "forged_rejection": forged["receipt"]["rejection_reason"],
        "bogus_hash_rejection": bogus["receipt"]["rejection_reason"],
        "policy": policy,
        "accepted_receipt_hash": accepted["receipt"]["receipt_hash"],
        "duplicate_same_origin_blocked": duplicate["duplicate"],
        "superseding_receipt_hash": new["receipt_hash"],
        "superseded_history_preserved": True,
        "active_verified_attempts_after_supersession": authority["attempts"],
        "restart_policy_count": len(restarted_store.verifier_policies()),
        "restart_receipts": restarted_receipts,
    }
    _write(root, "VERIFIER_AUTHORITY_BINDING.json", payload)
    return payload


def claim_identity_lineage(root: Path) -> dict[str, Any]:
    pair_provider = RecordingProvider()
    pair_engine = MiMicusEngine(f"sqlite:///{root / 'claim-pair.db'}", provider=pair_provider)
    pair = pair_engine.run(
        RunRequest(
            task="Assess this structured context.",
            domain="general",
            evidence=_evidence({"context": "paired identity probe"}, cluster="pair"),
            max_agents=2,
            depth="deep",
        )
    )
    assert pair.morphology == "paired_verify"
    assert pair.challenge_edge_count >= 1
    assert pair.falsifiers
    pair_full = pair_engine.get_run(pair.run_id)
    assert pair_full is not None
    pair_comms = pair_full["persistent_state"]["communications"]
    pair_claim_ids = {str(row["claim_hash"]) for row in pair.final_claims}
    assert pair_comms
    assert all(str(row["target_claim_hash"]) in pair_claim_ids for row in pair_comms)
    assert any(str(row["revision_before_hash"]) != str(row["revision_after_hash"]) for row in pair_comms)
    assert all(set(row["target_claim_hashes"]) <= pair_claim_ids for row in pair.falsifiers)

    sparse_provider = RecordingProvider()
    sparse_engine = MiMicusEngine(f"sqlite:///{root / 'claim-sparse.db'}", provider=sparse_provider)
    sparse_facts = _numeric() | {
        "evidence_date": "2026-08-17T00:00:00+00:00",
        "as_of": "2026-08-18T00:00:00+00:00",
        "absence_key": "target",
        "registry": {},
    }
    sparse = sparse_engine.run(
        RunRequest(
            task="Assess this structured context.",
            domain="research",
            evidence=_evidence(sparse_facts, cluster="sparse"),
            max_agents=4,
            depth="deep",
            learn=True,
        )
    )
    assert sparse.morphology == "sparse_graph"
    assert sparse.challenge_edge_count >= 1
    numeric_exec = next(row for row in sparse.falsifiers if row["primitive"] == "numeric_invariant" and row["verdict"] == "PASS")
    target_hash = str(numeric_exec["target_claim_hashes"][0])
    sparse_claim = next(row for row in sparse.final_claims if row["claim_hash"] == target_hash)
    sparse_full = sparse_engine.get_run(sparse.run_id)
    assert sparse_full is not None
    sparse_comms = sparse_full["persistent_state"]["communications"]
    assert all(str(row["target_claim_hash"]) in {c["claim_hash"] for c in sparse.final_claims} for row in sparse_comms)
    assert target_hash in set(sparse.swarm_decision["selected_claim_hashes"]) | {c["claim_hash"] for c in sparse.final_claims}

    token = "order007-lineage-oracle-token-v1"
    sparse_engine.register_verifier_authority(
        verifier_id="oracle:order007-lineage",
        authority_class="deterministic_oracle",
        source_independence_cluster="order007-lineage-v1",
        auth_token=token,
    )
    verified = sparse_engine.submit_verification(
        _receipt(
            sparse,
            sparse_claim,
            verifier_id="oracle:order007-lineage",
            token=token,
            status="FALSIFIED",
            cluster="order007-lineage-v1",
            snapshot_hashes=(str(numeric_exec["execution_snapshot_hash"]),),
        )
    )
    assert verified["accepted"] is True
    assert verified["germinal"] is not None
    assert verified["germinal"]["parent_hash"] == numeric_exec["spec_hash"]
    payload = {
        "pass": True,
        "paired": {
            "run_id": pair.run_id,
            "morphology": pair.morphology,
            "claim_identity_hashes": sorted(pair_claim_ids),
            "falsifier_targets": sorted({h for row in pair.falsifiers for h in row["target_claim_hashes"]}),
            "communications": pair_comms,
        },
        "sparse": {
            "run_id": sparse.run_id,
            "morphology": sparse.morphology,
            "target_claim_identity_hash": target_hash,
            "claim_revision_hash": sparse_claim["claim_revision_hash"],
            "falsifier_execution_snapshot_hash": numeric_exec["execution_snapshot_hash"],
            "communications": sparse_comms,
            "receipt_hash": verified["receipt"]["receipt_hash"],
            "germinal": verified["germinal"],
        },
    }
    _write(root, "CLAIM_IDENTITY_LINEAGE.json", payload)
    return payload


def _spec(spec_id: str, tolerance: float, eig: float) -> FalsifierSpec:
    return FalsifierSpec(
        id=spec_id,
        version="7.0",
        domain="test",
        trigger="verify structured evidence against the sealed claim",
        primitive="numeric_invariant",
        params={"relative_tolerance": tolerance},
        oracle_kind="deterministic",
        expected_information_gain=eig,
        estimated_cost=0.0,
        estimated_latency=1.0,
        provenance="ORDER-007-evidence",
    )


def claim_market_novelty(root: Path) -> dict[str, Any]:
    provider = RecordingProvider()
    engine = MiMicusEngine(f"sqlite:///{root / 'market.db'}", provider=provider)
    task = "Assess this supplied material."
    run = engine.run(
        RunRequest(
            task=task,
            domain="finance",
            evidence=_evidence(_numeric(), cluster="market"),
            max_agents=2,
            depth="deep",
        )
    )
    selected = run.evidence_provenance["claim_aware_market"]["selected"]
    candidates = run.evidence_provenance["claim_aware_market"]["candidates"]
    assert all(word not in task.lower() for word in ("numeric", "price", "revenue", "tam", "12x"))
    assert any(row["spec_hash"] == exec_row["spec_hash"] for row in selected for exec_row in run.falsifiers if exec_row["primitive"] == "numeric_invariant")
    assert selected and all("novelty=" in row["selection_reason"] for row in selected)

    first = _spec("N1", 0.05, 0.90)
    near = _spec("N2", 0.051, 0.91)
    claims = [
        Claim(statement="numeric-a", domain="test", probability=0.51, claim_type="numeric"),
        Claim(statement="numeric-b", domain="test", probability=0.95, claim_type="numeric"),
    ]
    market = FalsifierMarket()
    retained, all_bids = market.select_for_claims(
        [first, near],
        claims,
        evidence=_numeric(),
        budget_usd=1.0,
        max_tests=4,
    )
    retained_specs = {row.spec_hash for row in retained}
    assert len(retained_specs) == 1
    flipped = [claims[0].model_copy(update={"probability": 0.99}), claims[1].model_copy(update={"probability": 0.52})]
    retained_flipped, _ = market.select_for_claims([first], flipped, evidence=_numeric(), budget_usd=1.0, max_tests=2)
    assert retained and retained_flipped
    assert retained[0].target_claim_hash != retained_flipped[0].target_claim_hash
    payload = {
        "pass": True,
        "runtime_run_id": run.run_id,
        "task_text": task,
        "runtime_selected": selected,
        "runtime_candidate_count": len(candidates),
        "near_duplicate_retained_specs": sorted(retained_specs),
        "near_duplicate_candidate_count": len(all_bids),
        "probability_reordered_target": retained_flipped[0].target_claim_hash,
    }
    _write(root, "CLAIM_MARKET_NOVELTY.json", payload)
    return payload


def hierarchy_complete_execution(root: Path) -> dict[str, Any]:
    facts = _numeric() | {
        "evidence_date": "2026-08-17T00:00:00+00:00",
        "as_of": "2026-08-18T00:00:00+00:00",
        "clusters": ["primary-a", "primary-b"],
        "texts": ["alpha", "beta"],
        "claim_figure": 42,
        "evidence_spans": [{"span_id": "s1", "supported_figures": [42], "material_support": True}],
        "absence_key": "missing",
        "registry": {},
        "registry_snapshot_hash": "d" * 64,
    }
    provider = RecordingProvider()
    engine = MiMicusEngine(f"sqlite:///{root / 'hierarchy.db'}", provider=provider)
    run = engine.run(
        RunRequest(
            task="Evaluate the supplied structured material.",
            domain="research",
            evidence=_evidence(facts, cluster="hierarchy"),
            max_agents=4,
            max_concurrency=4,
            depth="deep",
        )
    )
    assert run.morphology == "hierarchical_fanout_fanin"
    hx = run.hierarchy_execution
    assert len(hx["required_subtasks"]) >= 6
    assert hx["complete"] is True
    assert hx["unresolved_subtasks"] == []
    assert set(hx["required_subtasks"]) == set(hx["executed_subtasks"])
    assert set(hx["required_subtasks"]) == set(hx["assigned_subtasks"])

    candidates = {row.fingerprint: row for row in engine.services.agent_factory.candidates()}
    subtasks_by_hash = {row["subtask_hash"]: row for row in run.subtasks}
    for claim in run.final_claims:
        subtask_hash = claim.get("subtask_hash")
        if not subtask_hash:
            continue
        required = set(subtasks_by_hash[subtask_hash]["required_capabilities"])
        actual = set(candidates[str(claim["contributor_fingerprint"])].capabilities)
        assert required <= actual

    scope_by_objective = {row["objective"]: set(row["evidence_scope"]) for row in run.subtasks}
    scoped_requests: list[dict[str, Any]] = []
    for request in provider.requests:
        if request["task"] not in scope_by_objective:
            continue
        scope = scope_by_objective[request["task"]]
        observed = set(request["evidence_keys"])
        assert observed <= scope
        scoped_requests.append(request | {"declared_scope": sorted(scope)})
    assert len(scoped_requests) == len(run.subtasks)

    group_by_subtask = {row["subtask_hash"]: row["dependency_group"] for row in run.subtasks}
    group_by_node = {str(claim["contributor_node_id"]): group_by_subtask[str(claim["subtask_hash"])] for claim in run.final_claims if claim.get("subtask_hash")}
    for group_name, result in hx["subgroup_results"].items():
        expected = group_name.split("subgroup:", 1)[1]
        assert all(group_by_node[str(node_id)] == expected for node_id in result["claims"])

    incomplete = MiMicusEngine(
        f"sqlite:///{root / 'hierarchy-incomplete.db'}",
        provider=RecordingProvider(),
    ).run(
        RunRequest(
            task="Evaluate the supplied structured material.",
            domain="research",
            evidence=_evidence(facts, cluster="hierarchy-incomplete"),
            max_agents=3,
            max_concurrency=3,
            depth="deep",
        )
    )
    assert incomplete.morphology == "hierarchical_fanout_fanin"
    assert incomplete.hierarchy_execution["complete"] is False
    assert incomplete.hierarchy_execution["unresolved_subtasks"]
    assert incomplete.status == "inconclusive"
    assert incomplete.swarm_decision["epistemic_status"] == "INCONCLUSIVE"
    payload = {
        "pass": True,
        "complete_run_id": run.run_id,
        "required_subtasks": hx["required_subtasks"],
        "assigned_subtasks": hx["assigned_subtasks"],
        "executed_subtasks": hx["executed_subtasks"],
        "subgroup_results": hx["subgroup_results"],
        "scoped_provider_requests": scoped_requests,
        "incomplete_run_id": incomplete.run_id,
        "incomplete_unresolved_subtasks": incomplete.hierarchy_execution["unresolved_subtasks"],
        "incomplete_status": incomplete.status,
    }
    _write(root, "HIERARCHY_COMPLETE_EXECUTION.json", payload)
    return payload


def _removal_case(root: Path, *, name: str, same_statement: bool) -> dict[str, Any]:
    db = f"sqlite:///{root / f'{name}.db'}"
    provider = RecordingProvider(same_statement=same_statement)
    engine = MiMicusEngine(db, provider=provider)
    run = engine.run(
        RunRequest(
            task="Assess this structured context.",
            domain="general",
            evidence=_evidence({"context": name}, cluster=name),
            max_agents=2,
            depth="normal",
            learn=True,
        )
    )
    assert run.morphology == "paired_verify"
    assert len(run.final_claims) >= 2
    claim = run.final_claims[0]
    token = f"order007-removal-{name}-token-v1"
    verifier_id = f"oracle:order007-removal:{name}"
    cluster = f"order007-removal-{name}"
    engine.register_verifier_authority(
        verifier_id=verifier_id,
        authority_class="deterministic_oracle",
        source_independence_cluster=cluster,
        auth_token=token,
    )
    accepted = engine.submit_verification(
        _receipt(
            run,
            claim,
            verifier_id=verifier_id,
            token=token,
            status="SUPPORTED",
            cluster=cluster,
        )
    )
    assert accepted["accepted"] is True
    rows = accepted["removal_attributions"]
    assert rows
    target_fp = str(claim["contributor_fingerprint"])
    target_rows = [row for row in rows if row["fingerprint"] == target_fp]
    assert target_rows
    return {
        "run_id": run.run_id,
        "target_fingerprint": target_fp,
        "rows": rows,
        "learned_state": SwarmStateStore(engine.repository.engine).learned_state("general"),
    }


def removal_attribution(root: Path) -> dict[str, Any]:
    redundant = _removal_case(root, name="redundant", same_statement=True)
    decisive = _removal_case(root, name="decisive", same_statement=False)
    rows = [*redundant["rows"], *decisive["rows"]]
    assert rows
    assert all(-1.0 <= float(row["marginal_delta"]) <= 1.0 for row in rows)
    assert all(row["method"] == "production_decision_leave_one_out_v2" for row in rows)
    assert all(len(str(row["decision_before_hash"])) == 64 for row in rows)
    assert all(len(str(row["decision_without_hash"])) == 64 for row in rows)
    assert all(row["verified_scope"] for row in rows)
    payload = {
        "pass": True,
        "redundant": redundant,
        "decisive": decisive,
        "min_delta": min(float(row["marginal_delta"]) for row in rows),
        "max_delta": max(float(row["marginal_delta"]) for row in rows),
        "method": "production_decision_leave_one_out_v2",
    }
    _write(root, "REMOVAL_ATTRIBUTION.json", payload)
    return payload


def runtime_core_lock(root: Path) -> dict[str, Any]:
    rejected: list[str] = []
    for kwargs in (
        {"source_mode": "runtime", "core_semantics": False},
        {"source_mode": "runtime", "fixture": {"price": 1}},
    ):
        try:
            RunRequest(task="x", **kwargs)
        except ValidationError as exc:
            rejected.append(str(exc.errors()[0]["ctx"]["error"]))
        else:
            raise AssertionError(f"runtime downgrade unexpectedly accepted: {kwargs}")
    engine = MiMicusEngine(f"sqlite:///{root / 'runtime-lock.db'}")
    runtime = engine.run(RunRequest(task="Assess this input.", source_mode="runtime"))
    assert runtime.evidence_provenance["source_mode"] == "runtime"
    assert runtime.threat_profile and runtime.swarm_decision

    task_file = root / "runtime-downgrade.json"
    task_file.write_text(json.dumps({"task": "x", "fixture": {"price": 1}}), encoding="utf-8")
    cli = subprocess.run(
        [sys.executable, "-m", "mimicus.interfaces.cli", "run", "--profile", "offline", "--task-file", str(task_file)],
        text=True,
        capture_output=True,
        check=False,
    )
    assert cli.returncode != 0
    assert "cannot enter fixture/legacy semantics" in (cli.stdout + cli.stderr)
    payload = {
        "pass": True,
        "python_rejections": rejected,
        "runtime_run_id": runtime.run_id,
        "runtime_morphology": runtime.morphology,
        "runtime_source_mode": runtime.evidence_provenance["source_mode"],
        "cli_downgrade_exit_code": cli.returncode,
        "cli_downgrade_rejected": True,
    }
    _write(root, "RUNTIME_CORE_LOCK.json", payload)
    return payload


def run(root: Path) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)
    payloads = {
        "F032": verifier_authority_binding(root),
        "F033": claim_identity_lineage(root),
        "F034": claim_market_novelty(root),
        "F035": hierarchy_complete_execution(root),
        "F036": removal_attribution(root),
        "F037": runtime_core_lock(root),
    }
    summary = {"pass": all(row["pass"] for row in payloads.values()), "findings": payloads}
    assert summary["pass"] is True
    return summary


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("evidence/ORDER-007")
    summary = run(root)
    print(json.dumps({"ORDER_007_EVIDENCE": "PASS", "findings": sorted(summary["findings"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
