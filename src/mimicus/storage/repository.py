from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, delete, insert, select, update
from sqlalchemy.engine import Connection, Engine, make_url
from sqlalchemy.pool import StaticPool

from mimicus.agents.identity import AgentIdentity
from mimicus.canonical import canonical_json, sha256_obj
from mimicus.events.ledger import LedgerEvent
from mimicus.falsifiers.spec import FalsifierExecution, FalsifierSpec
from mimicus.memory.models import MemoryItem
from mimicus.storage.models import (
    AgentBankruptcyRow,
    AgentDomainCalibrationRow,
    AgentFingerprintRow,
    AgentLineageMemberRow,
    AgentLineageRow,
    Base,
    ClaimRow,
    CoalitionRow,
    CommunicationRow,
    EvasionEventRow,
    EventRow,
    EvidenceRow,
    FalsifierExecutionRow,
    FalsifierSpecRow,
    FalsifierVersionRow,
    FossilClaimRow,
    MemoryItemRow,
    MemoryLinkRow,
    MemoryTransitionRow,
    MutationCandidateRow,
    ProgressLedgerRow,
    RunRow,
    TaskLedgerRow,
)


def normalized_database_url(database_url: str) -> str:
    url = make_url(database_url)
    if url.drivername == "postgres":
        url = url.set(drivername="postgresql+psycopg")
    return str(url)


def make_engine(database_url: str) -> Engine:
    url = normalized_database_url(database_url)
    kwargs: dict[str, Any] = {"future": True}
    if url == "sqlite:///:memory:":
        kwargs.update(connect_args={"check_same_thread": False}, poolclass=StaticPool)
    elif url.startswith("sqlite:///"):
        path = Path(url.removeprefix("sqlite:///"))
        if path.parent != Path("."):
            path.parent.mkdir(parents=True, exist_ok=True)
        kwargs.update(connect_args={"check_same_thread": False})
    return create_engine(url, **kwargs)


def create_schema(engine: Engine) -> None:
    Base.metadata.create_all(engine)


def _now() -> str:
    return datetime.now(UTC).isoformat()


class Repository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.engine = make_engine(database_url)
        create_schema(self.engine)

    def register_identity(self, identity: AgentIdentity) -> None:
        recomputed = identity.recompute_fingerprint()
        if identity.fingerprint != recomputed:
            raise ValueError("agent fingerprint/material manifest mismatch")
        with self.engine.begin() as connection:
            fingerprint = connection.execute(select(AgentFingerprintRow.fingerprint).where(AgentFingerprintRow.fingerprint == identity.fingerprint)).scalar_one_or_none()
            manifest = canonical_json(
                {
                    "fingerprint": identity.fingerprint,
                    "recomputed_fingerprint": recomputed,
                    "fingerprint_matches_manifest": True,
                    "material_manifest": identity.material_manifest,
                    "lineage_id": identity.lineage_id,
                    "provider": identity.provider,
                    "model_family": identity.model_family,
                    "phenotype": identity.phenotype,
                    "tool_policy_hash": identity.tool_policy_hash,
                    "runtime_model_version": identity.runtime_model_version,
                    "phenotype_version": identity.phenotype_version,
                    "system_prompt_hash": identity.system_prompt_hash,
                    "tool_manifest_hash": identity.tool_manifest_hash,
                    "policy_hash": identity.policy_hash,
                    "provider_adapter_version": identity.provider_adapter_version,
                    "parent_fingerprint": identity.parent_fingerprint,
                    "revision_provenance": identity.revision_provenance,
                }
            )
            if fingerprint is not None:
                existing_manifest = connection.execute(select(AgentFingerprintRow.manifest_json).where(AgentFingerprintRow.fingerprint == identity.fingerprint)).scalar_one()
                parsed_manifest = json.loads(existing_manifest)
                if parsed_manifest.get("material_manifest") != identity.material_manifest or parsed_manifest.get("recomputed_fingerprint") != recomputed:
                    raise ValueError("agent fingerprint manifest drift detected")
            if fingerprint is None:
                connection.execute(
                    insert(AgentFingerprintRow).values(
                        fingerprint=identity.fingerprint,
                        provider=identity.provider,
                        model=identity.model_family,
                        manifest_json=manifest,
                    )
                )
            lineage = connection.execute(select(AgentLineageRow.lineage_id).where(AgentLineageRow.lineage_id == identity.lineage_id)).scalar_one_or_none()
            if lineage is None:
                connection.execute(
                    insert(AgentLineageRow).values(
                        lineage_id=identity.lineage_id,
                        provider=identity.provider,
                        model_family=identity.model_family,
                        phenotype=identity.phenotype,
                        tool_policy_hash=identity.tool_policy_hash,
                        provenance=identity.revision_provenance,
                        manifest_hash=identity.manifest_hash,
                        created_at=identity.created_at,
                    )
                )
            member = connection.execute(select(AgentLineageMemberRow.fingerprint).where(AgentLineageMemberRow.fingerprint == identity.fingerprint)).scalar_one_or_none()
            if member is None:
                connection.execute(
                    insert(AgentLineageMemberRow).values(
                        fingerprint=identity.fingerprint,
                        lineage_id=identity.lineage_id,
                        parent_fingerprint=identity.parent_fingerprint,
                        revision_provenance=identity.revision_provenance,
                        identity_manifest_hash=identity.manifest_hash,
                    )
                )
            else:
                existing = connection.execute(
                    select(AgentLineageMemberRow.lineage_id, AgentLineageMemberRow.identity_manifest_hash).where(AgentLineageMemberRow.fingerprint == identity.fingerprint)
                ).one()
                if existing.lineage_id != identity.lineage_id or existing.identity_manifest_hash != identity.manifest_hash:
                    raise ValueError("agent lineage metadata tamper detected")

    def lineage_id_for(self, fingerprint: str) -> str | None:
        with self.engine.connect() as connection:
            return connection.execute(select(AgentLineageMemberRow.lineage_id).where(AgentLineageMemberRow.fingerprint == fingerprint)).scalar_one_or_none()

    def lineage_has_bankrupt_predecessor(self, lineage_id: str, domain: str, *, exclude_fingerprint: str | None = None) -> bool:
        with self.engine.connect() as connection:
            rows = connection.execute(
                select(AgentLineageMemberRow.fingerprint, AgentBankruptcyRow.state)
                .join(AgentBankruptcyRow, AgentBankruptcyRow.fingerprint == AgentLineageMemberRow.fingerprint)
                .where(AgentLineageMemberRow.lineage_id == lineage_id, AgentBankruptcyRow.domain == domain)
            ).all()
        return any(state == "BANKRUPT" and fingerprint != exclude_fingerprint for fingerprint, state in rows)

    def calibration(self, fingerprint: str, domain: str) -> dict[str, Any]:
        with self.engine.connect() as connection:
            row = connection.execute(
                select(
                    AgentDomainCalibrationRow.fingerprint,
                    AgentDomainCalibrationRow.domain,
                    AgentDomainCalibrationRow.attempts,
                    AgentDomainCalibrationRow.successes,
                    AgentDomainCalibrationRow.failures,
                    AgentDomainCalibrationRow.brier_sum,
                    AgentDomainCalibrationRow.canary_failure_streak,
                    AgentDomainCalibrationRow.last_verified_at,
                ).where(AgentDomainCalibrationRow.fingerprint == fingerprint, AgentDomainCalibrationRow.domain == domain)
            ).one_or_none()
        if row is None:
            return {
                "fingerprint": fingerprint,
                "domain": domain,
                "attempts": 0,
                "successes": 0,
                "failures": 0,
                "brier_sum": 0.0,
                "canary_failure_streak": 0,
                "last_verified_at": None,
            }
        return {
            "fingerprint": row.fingerprint,
            "domain": row.domain,
            "attempts": row.attempts,
            "successes": row.successes,
            "failures": row.failures,
            "brier_sum": row.brier_sum,
            "canary_failure_streak": row.canary_failure_streak,
            "last_verified_at": row.last_verified_at,
        }

    def record_calibration(self, fingerprint: str, domain: str, *, predicted_probability: float, outcome: bool, canary: bool) -> dict[str, Any]:
        current = self.calibration(fingerprint, domain)
        p = min(1.0, max(0.0, predicted_probability))
        y = 1.0 if outcome else 0.0
        next_row = {
            "fingerprint": fingerprint,
            "domain": domain,
            "attempts": int(current["attempts"]) + 1,
            "successes": int(current["successes"]) + int(outcome),
            "failures": int(current["failures"]) + int(not outcome),
            "brier_sum": float(current["brier_sum"]) + (p - y) ** 2,
            "canary_failure_streak": (0 if outcome else int(current["canary_failure_streak"]) + 1) if canary else int(current["canary_failure_streak"]),
            "last_verified_at": _now(),
        }
        with self.engine.begin() as connection:
            existing = connection.execute(
                select(AgentDomainCalibrationRow.id).where(AgentDomainCalibrationRow.fingerprint == fingerprint, AgentDomainCalibrationRow.domain == domain)
            ).scalar_one_or_none()
            if existing is None:
                connection.execute(insert(AgentDomainCalibrationRow).values(**next_row))
            else:
                connection.execute(update(AgentDomainCalibrationRow).where(AgentDomainCalibrationRow.id == existing).values(**next_row))
        return next_row

    def bankruptcy_state(self, fingerprint: str, domain: str) -> str:
        with self.engine.connect() as connection:
            state = connection.execute(
                select(AgentBankruptcyRow.state).where(AgentBankruptcyRow.fingerprint == fingerprint, AgentBankruptcyRow.domain == domain)
            ).scalar_one_or_none()
        return str(state or "ACTIVE")

    def set_bankruptcy_state(self, fingerprint: str, domain: str, state: str, reason: str) -> None:
        if state not in {"ACTIVE", "BANKRUPT", "PROBATION"}:
            raise ValueError("invalid bankruptcy/probation state")
        with self.engine.begin() as connection:
            existing = connection.execute(
                select(AgentBankruptcyRow.id).where(AgentBankruptcyRow.fingerprint == fingerprint, AgentBankruptcyRow.domain == domain)
            ).scalar_one_or_none()
            values = {"fingerprint": fingerprint, "domain": domain, "state": state, "reason": reason, "updated_at": _now()}
            if existing is None:
                connection.execute(insert(AgentBankruptcyRow).values(**values))
            else:
                connection.execute(update(AgentBankruptcyRow).where(AgentBankruptcyRow.id == existing).values(**values))

    def save_memory_transition(self, item: MemoryItem, *, reason: str, from_status: str | None = None) -> None:
        payload = item.model_dump(mode="json")
        transition_hash = sha256_obj({"memory_id": item.memory_id, "from": from_status, "to": item.status.value, "reason": reason, "payload": payload})
        with self.engine.begin() as connection:
            self._upsert_memory(connection, item)
            seen = connection.execute(select(MemoryTransitionRow.id).where(MemoryTransitionRow.transition_hash == transition_hash)).scalar_one_or_none()
            if seen is None:
                connection.execute(
                    insert(MemoryTransitionRow).values(
                        memory_id=item.memory_id,
                        from_status=from_status,
                        to_status=item.status.value,
                        reason=reason,
                        transition_hash=transition_hash,
                        created_at=_now(),
                    )
                )
            for parent in item.derived_from:
                if connection.execute(select(MemoryItemRow.memory_id).where(MemoryItemRow.memory_id == parent)).scalar_one_or_none() is not None:
                    link = connection.execute(
                        select(MemoryLinkRow.id).where(
                            MemoryLinkRow.parent_memory_id == parent,
                            MemoryLinkRow.child_memory_id == item.memory_id,
                            MemoryLinkRow.relation == "derived_from",
                        )
                    ).scalar_one_or_none()
                    if link is None:
                        connection.execute(insert(MemoryLinkRow).values(parent_memory_id=parent, child_memory_id=item.memory_id, relation="derived_from"))

    @staticmethod
    def _upsert_memory(connection: Connection, item: MemoryItem) -> None:
        existing = connection.execute(select(MemoryItemRow.memory_id).where(MemoryItemRow.memory_id == item.memory_id)).scalar_one_or_none()
        values = {
            "claim_hash": item.claim_hash,
            "domain": item.domain,
            "status": item.status.value,
            "authority": item.authority,
            "payload_json": canonical_json(item.model_dump(mode="json")),
            "updated_at": _now(),
        }
        if existing is None:
            connection.execute(insert(MemoryItemRow).values(memory_id=item.memory_id, **values))
        else:
            connection.execute(update(MemoryItemRow).where(MemoryItemRow.memory_id == item.memory_id).values(**values))

    def eligible_memory(self, domain: str) -> list[MemoryItem]:
        with self.engine.connect() as connection:
            rows = (
                connection.execute(
                    select(MemoryItemRow.payload_json).where(
                        MemoryItemRow.domain == domain,
                        MemoryItemRow.status.in_(["private_verified", "shared_verified"]),
                    )
                )
                .scalars()
                .all()
            )
        return [MemoryItem.model_validate(json.loads(payload)) for payload in rows]

    def persist_falsifier(self, spec: FalsifierSpec, *, lifecycle_state: str, domain: str, decision: dict[str, Any] | None = None) -> None:
        with self.engine.begin() as connection:
            self._persist_falsifier(connection, spec, lifecycle_state=lifecycle_state, domain=domain, decision=decision or {})

    @staticmethod
    def _persist_falsifier(connection: Connection, spec: FalsifierSpec, *, lifecycle_state: str, domain: str, decision: dict[str, Any]) -> None:
        existing = connection.execute(select(FalsifierSpecRow.spec_hash).where(FalsifierSpecRow.spec_hash == spec.hash)).scalar_one_or_none()
        if existing is None:
            connection.execute(
                insert(FalsifierSpecRow).values(
                    spec_hash=spec.hash,
                    spec_id=spec.id,
                    version=spec.version,
                    primitive=spec.primitive,
                    domain=domain,
                    parent_hash=spec.parent_hash,
                    payload_json=canonical_json(spec.model_dump(mode="json")),
                )
            )
        version = connection.execute(
            select(FalsifierVersionRow.id).where(FalsifierVersionRow.spec_hash == spec.hash, FalsifierVersionRow.lifecycle_state == lifecycle_state)
        ).scalar_one_or_none()
        if version is None:
            connection.execute(
                insert(FalsifierVersionRow).values(
                    spec_hash=spec.hash,
                    lifecycle_state=lifecycle_state,
                    decision_json=canonical_json(decision),
                    created_at=_now(),
                )
            )

    def promoted_falsifiers(self, domain: str) -> list[FalsifierSpec]:
        with self.engine.connect() as connection:
            rows = (
                connection.execute(
                    select(FalsifierSpecRow.payload_json)
                    .join(FalsifierVersionRow, FalsifierVersionRow.spec_hash == FalsifierSpecRow.spec_hash)
                    .where(FalsifierSpecRow.domain == domain, FalsifierVersionRow.lifecycle_state == "PROMOTE")
                )
                .scalars()
                .all()
            )
        unique: dict[str, FalsifierSpec] = {}
        for payload in rows:
            spec = FalsifierSpec.model_validate(json.loads(payload))
            unique[spec.hash] = spec
        return list(unique.values())

    def persist_germinal_decision(
        self,
        *,
        evasion_hash: str,
        parent_spec_hash: str,
        ground_truth_hash: str,
        evasion_payload: dict[str, Any],
        candidate_hash: str,
        candidate_spec: FalsifierSpec,
        status: str,
        metrics: dict[str, Any],
        domain: str,
    ) -> None:
        with self.engine.begin() as connection:
            existing_evasion = connection.execute(select(EvasionEventRow.evasion_hash).where(EvasionEventRow.evasion_hash == evasion_hash)).scalar_one_or_none()
            if existing_evasion is None:
                connection.execute(
                    insert(EvasionEventRow).values(
                        evasion_hash=evasion_hash,
                        parent_spec_hash=parent_spec_hash,
                        ground_truth_hash=ground_truth_hash,
                        confirmed=True,
                        payload_json=canonical_json(evasion_payload),
                    )
                )
            existing_candidate = connection.execute(select(MutationCandidateRow.candidate_hash).where(MutationCandidateRow.candidate_hash == candidate_hash)).scalar_one_or_none()
            values = {
                "parent_hash": parent_spec_hash,
                "status": status,
                "metrics_json": canonical_json(metrics),
                "spec_json": canonical_json(candidate_spec.model_dump(mode="json")),
                "evasion_hash": evasion_hash,
            }
            if existing_candidate is None:
                connection.execute(insert(MutationCandidateRow).values(candidate_hash=candidate_hash, **values))
            else:
                connection.execute(update(MutationCandidateRow).where(MutationCandidateRow.candidate_hash == candidate_hash).values(**values))
            if status == "PROMOTE":
                self._persist_falsifier(connection, candidate_spec, lifecycle_state="PROMOTE", domain=domain, decision=metrics)

    def seed_fossil(self, fossil_hash: str, primitive: str, expected_verdict: str, payload: dict[str, Any]) -> None:
        with self.engine.begin() as connection:
            if connection.execute(select(FossilClaimRow.fossil_hash).where(FossilClaimRow.fossil_hash == fossil_hash)).scalar_one_or_none() is None:
                connection.execute(
                    insert(FossilClaimRow).values(
                        fossil_hash=fossil_hash,
                        primitive=primitive,
                        expected_verdict=expected_verdict,
                        payload_json=canonical_json(payload),
                    )
                )

    def save_run_bundle(
        self,
        *,
        run_id: str,
        task_hash: str,
        config_hash: str,
        status: str,
        ledger_head: str,
        result: dict[str, Any],
        events: list[LedgerEvent],
        task_ledger: dict[str, Any] | None = None,
        progress_rows: list[dict[str, Any]] | None = None,
        coalition: dict[str, Any] | None = None,
        plan_hash: str | None = None,
        plan: dict[str, Any] | None = None,
        communications: list[dict[str, Any]] | None = None,
        claims: list[dict[str, Any]] | None = None,
        evidence: list[dict[str, Any]] | None = None,
        executions: list[FalsifierExecution] | None = None,
    ) -> None:
        with self.engine.begin() as connection:
            if connection.execute(select(RunRow.run_id).where(RunRow.run_id == run_id)).scalar_one_or_none() is not None:
                raise ValueError(f"run already exists: {run_id}")
            connection.execute(
                insert(RunRow).values(
                    run_id=run_id,
                    task_hash=task_hash,
                    config_hash=config_hash,
                    status=status,
                    ledger_head=ledger_head,
                    result_json=canonical_json(result),
                    created_at=_now(),
                )
            )
            for event in events:
                connection.execute(
                    insert(EventRow).values(
                        run_id=run_id,
                        sequence=event.sequence,
                        event_type=event.event_type,
                        event_hash=event.event_hash,
                        prev_event_hash=event.prev_event_hash,
                        event_json=event.model_dump_json(),
                    )
                )
            if task_ledger is not None:
                connection.execute(insert(TaskLedgerRow).values(run_id=run_id, payload_json=canonical_json(task_ledger)))
            for index, progress in enumerate(progress_rows or []):
                connection.execute(insert(ProgressLedgerRow).values(run_id=run_id, step=index, payload_json=canonical_json(progress)))
            if coalition is not None:
                connection.execute(
                    insert(CoalitionRow).values(
                        run_id=run_id,
                        topology=str(coalition.get("topology") or coalition.get("morphology") or "unknown"),
                        members_json=canonical_json(coalition.get("members", [])),
                        rationale_json=canonical_json(coalition.get("rationale", {})),
                        plan_hash=plan_hash,
                        plan_json=canonical_json(plan or {}),
                    )
                )
            for row in communications or []:
                connection.execute(
                    insert(CommunicationRow).values(
                        run_id=run_id,
                        round_no=int(row.get("round", 1)),
                        source_fp=str(row.get("source_fp", "")),
                        target_fp=str(row.get("target_fp", "")),
                        reason=str(row.get("reason", "")),
                        provider_call_id=row.get("provider_call_id"),
                        input_hash=row.get("input_hash"),
                        output_hash=row.get("output_hash"),
                        payload_json=canonical_json(row),
                    )
                )
            for claim in claims or []:
                claim_hash = str(claim.get("claim_hash") or sha256_obj(claim))
                if connection.execute(select(ClaimRow.claim_hash).where(ClaimRow.claim_hash == claim_hash)).scalar_one_or_none() is None:
                    connection.execute(
                        insert(ClaimRow).values(
                            claim_hash=claim_hash,
                            run_id=run_id,
                            status=str(claim.get("status", "proposed")),
                            payload_json=canonical_json(claim),
                        )
                    )
            for item in evidence or []:
                evidence_hash = str(item.get("evidence_hash") or sha256_obj(item))
                if connection.execute(select(EvidenceRow.evidence_hash).where(EvidenceRow.evidence_hash == evidence_hash)).scalar_one_or_none() is None:
                    connection.execute(
                        insert(EvidenceRow).values(
                            evidence_hash=evidence_hash,
                            run_id=run_id,
                            independence_cluster=str(item.get("independence_cluster", "unknown")),
                            payload_json=canonical_json(item),
                        )
                    )
            for execution in executions or []:
                if (
                    connection.execute(select(FalsifierExecutionRow.id).where(FalsifierExecutionRow.snapshot_hash == execution.execution_snapshot_hash)).scalar_one_or_none()
                    is None
                ):
                    connection.execute(
                        insert(FalsifierExecutionRow).values(
                            run_id=run_id,
                            spec_hash=execution.spec_hash,
                            snapshot_hash=execution.execution_snapshot_hash,
                            verdict=execution.verdict.value,
                            payload_json=canonical_json(execution.model_dump(mode="json")),
                        )
                    )

    def save_run(self, *, run_id: str, task_hash: str, config_hash: str, status: str, ledger_head: str, result: dict[str, Any], events: list[LedgerEvent]) -> None:
        self.save_run_bundle(
            run_id=run_id,
            task_hash=task_hash,
            config_hash=config_hash,
            status=status,
            ledger_head=ledger_head,
            result=result,
            events=events,
        )

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self.engine.connect() as connection:
            row = connection.execute(select(RunRow.result_json).where(RunRow.run_id == run_id)).scalar_one_or_none()
        return None if row is None else json.loads(row)

    def get_events(self, run_id: str) -> list[dict[str, Any]]:
        with self.engine.connect() as connection:
            rows = connection.execute(select(EventRow.event_json).where(EventRow.run_id == run_id).order_by(EventRow.sequence)).scalars().all()
        return [json.loads(row) for row in rows]

    def get_evidence(self, run_id: str) -> list[dict[str, Any]]:
        with self.engine.connect() as connection:
            rows = connection.execute(select(EvidenceRow.payload_json).where(EvidenceRow.run_id == run_id).order_by(EvidenceRow.evidence_hash)).scalars().all()
        return [json.loads(row) for row in rows]

    def resolve_evidence(self, run_id: str, evidence_hashes: list[str]) -> dict[str, dict[str, Any]]:
        wanted = set(evidence_hashes)
        return {str(row.get("evidence_hash")): row for row in self.get_evidence(run_id) if str(row.get("evidence_hash")) in wanted}

    def inspect_state(self, run_id: str | None = None) -> dict[str, Any]:
        with self.engine.connect() as connection:
            runs = connection.execute(select(RunRow.run_id)).scalars().all()
            memories = connection.execute(select(MemoryItemRow.memory_id, MemoryItemRow.status, MemoryItemRow.domain)).all()
            specs = connection.execute(select(FalsifierSpecRow.spec_hash, FalsifierSpecRow.version, FalsifierSpecRow.domain)).all()
            bankruptcies = connection.execute(select(AgentBankruptcyRow.fingerprint, AgentBankruptcyRow.domain, AgentBankruptcyRow.state)).all()
            lineages = connection.execute(select(AgentLineageMemberRow.fingerprint, AgentLineageMemberRow.lineage_id)).all()
            identity_manifests = connection.execute(select(AgentFingerprintRow.manifest_json)).scalars().all()
            communications: list[str] = []
            evidence_rows: list[str] = []
            if run_id is not None:
                communication_rows = connection.execute(select(CommunicationRow.payload_json).where(CommunicationRow.run_id == run_id)).scalars().all()
                communications = [str(row) for row in communication_rows if row is not None]
                raw_evidence = connection.execute(select(EvidenceRow.payload_json).where(EvidenceRow.run_id == run_id)).scalars().all()
                evidence_rows = [str(row) for row in raw_evidence if row is not None]
        return {
            "run_count": len(runs),
            "memory": [{"memory_id": a, "status": b, "domain": c} for a, b, c in memories],
            "falsifiers": [{"spec_hash": a, "version": b, "domain": c} for a, b, c in specs],
            "bankruptcy": [{"fingerprint": a, "domain": b, "state": c} for a, b, c in bankruptcies],
            "lineages": [{"fingerprint": a, "lineage_id": b} for a, b in lineages],
            "identities": [json.loads(row) for row in identity_manifests],
            "communications": [json.loads(row) for row in communications if row],
            "evidence": [json.loads(row) for row in evidence_rows if row],
        }

    def reset_run_for_test(self, run_id: str) -> None:
        with self.engine.begin() as connection:
            connection.execute(delete(RunRow).where(RunRow.run_id == run_id))
