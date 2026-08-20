from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.engine import Engine

from mimicus.canonical import canonical_json, sha256_obj
from mimicus.memory.models import MemoryItem
from mimicus.storage.models import EvasionEventRow, FalsifierVersionRow, MemoryItemRow, MutationCandidateRow
from mimicus.storage.swarm_models import ReceiptGerminalOutcomeRow, RemovalAttributionRow, VerificationReceiptRow
from mimicus.types import MemoryStatus


def _now() -> str:
    return datetime.now(UTC).isoformat()


def active_receipts_for_run(engine: Engine, run_id: str) -> list[dict[str, Any]]:
    with engine.connect() as connection:
        rows = (
            connection.execute(
                select(
                    VerificationReceiptRow.receipt_hash,
                    VerificationReceiptRow.claim_hash,
                    VerificationReceiptRow.payload_json,
                    VerificationReceiptRow.learning_active,
                ).where(
                    VerificationReceiptRow.run_id == run_id,
                    VerificationReceiptRow.accepted == 1,
                    VerificationReceiptRow.learning_active == 1,
                )
            )
            .mappings()
            .all()
        )
    out: list[dict[str, Any]] = []
    for row in rows:
        payload = json.loads(str(row["payload_json"]))
        out.append(
            payload
            | {
                "receipt_hash": str(row["receipt_hash"]),
                "claim_hash": str(row["claim_hash"]),
                "learning_active": bool(row["learning_active"]),
            }
        )
    return out


def active_receipt_for_origin(engine: Engine, *, run_id: str, claim_hash: str, adjudication_origin_hash: str) -> dict[str, Any] | None:
    for row in active_receipts_for_run(engine, run_id):
        if row.get("claim_hash") == claim_hash and row.get("adjudication_origin_hash") == adjudication_origin_hash:
            return row
    return None


def complete_active_scope(engine: Engine, *, run_id: str, required_claim_hashes: list[str] | tuple[str, ...]) -> dict[str, str] | None:
    required = {str(value) for value in required_claim_hashes if value}
    if not required:
        return None
    by_claim: dict[str, list[str]] = {}
    for row in active_receipts_for_run(engine, run_id):
        by_claim.setdefault(str(row["claim_hash"]), []).append(str(row["receipt_hash"]))
    if not required <= set(by_claim):
        return None
    return {claim_hash: sorted(by_claim[claim_hash])[0] for claim_hash in sorted(required)}


def _memory_depends_on_receipt(payload_json: str, receipt_hash: str) -> bool:
    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError:
        return False
    return receipt_hash in {str(value) for value in payload.get("derived_from", [])}


def revoke_receipt_derivatives(engine: Engine, receipt_hash: str, superseded_by_hash: str) -> dict[str, int]:
    counts = {"removals": 0, "memory": 0, "evasions": 0, "mutations": 0, "promotions": 0, "germinal": 0}
    with engine.begin() as connection:
        receipt_target = (
            connection.execute(select(VerificationReceiptRow.run_id, VerificationReceiptRow.claim_hash).where(VerificationReceiptRow.receipt_hash == receipt_hash))
            .mappings()
            .one_or_none()
        )
        revoked_run_id = None if receipt_target is None else str(receipt_target["run_id"])
        revoked_claim_hash = None if receipt_target is None else str(receipt_target["claim_hash"])
        removal_rows = (
            connection.execute(
                select(
                    RemovalAttributionRow.id,
                    RemovalAttributionRow.receipt_hash,
                    RemovalAttributionRow.run_id,
                    RemovalAttributionRow.verified_scope_json,
                    RemovalAttributionRow.marginal_delta,
                    RemovalAttributionRow.original_marginal_delta,
                    RemovalAttributionRow.active,
                )
            )
            .mappings()
            .all()
        )
        for row in removal_rows:
            scope_raw = row["verified_scope_json"]
            try:
                scope = set(json.loads(str(scope_raw))) if scope_raw else {receipt_hash}
            except json.JSONDecodeError:
                scope = {receipt_hash}
            if not bool(row["active"]):
                continue
            if revoked_run_id is not None and str(row["run_id"]) != revoked_run_id:
                continue
            depends_on_receipt = str(row["receipt_hash"]) == receipt_hash or receipt_hash in scope or (revoked_claim_hash is not None and revoked_claim_hash in scope)
            if not depends_on_receipt:
                continue
            original = row["original_marginal_delta"]
            if original is None:
                original = float(row["marginal_delta"])
            connection.execute(
                update(RemovalAttributionRow)
                .where(RemovalAttributionRow.id == row["id"])
                .values(
                    active=0,
                    original_marginal_delta=float(original),
                    marginal_delta=0.0,
                    provenance_hash=sha256_obj(
                        {
                            "state": "revoked_authority",
                            "receipt_hash": receipt_hash,
                            "superseded_by_hash": superseded_by_hash,
                            "scope": sorted(scope),
                        }
                    ),
                )
            )
            counts["removals"] += 1

        memories = connection.execute(select(MemoryItemRow.memory_id, MemoryItemRow.payload_json)).mappings().all()
        for row in memories:
            if not _memory_depends_on_receipt(str(row["payload_json"]), receipt_hash):
                continue
            item = MemoryItem.model_validate(json.loads(str(row["payload_json"])))
            if item.status in {MemoryStatus.REJECTED, MemoryStatus.EXPIRED}:
                continue
            rejected = item.model_copy(update={"status": MemoryStatus.REJECTED, "authority": 0.0})
            connection.execute(
                update(MemoryItemRow)
                .where(MemoryItemRow.memory_id == row["memory_id"])
                .values(
                    status=MemoryStatus.REJECTED.value,
                    authority=0.0,
                    payload_json=canonical_json(rejected.model_dump(mode="json")),
                    updated_at=_now(),
                )
            )
            counts["memory"] += 1

        evasion_hashes = list(
            connection.execute(
                select(EvasionEventRow.evasion_hash).where(
                    EvasionEventRow.ground_truth_hash == receipt_hash,
                    EvasionEventRow.confirmed.is_(True),
                )
            ).scalars()
        )
        if evasion_hashes:
            connection.execute(update(EvasionEventRow).where(EvasionEventRow.evasion_hash.in_(evasion_hashes)).values(confirmed=False))
            counts["evasions"] = len(evasion_hashes)
            mutation_hashes = list(connection.execute(select(MutationCandidateRow.candidate_hash).where(MutationCandidateRow.evasion_hash.in_(evasion_hashes))).scalars())
            if mutation_hashes:
                connection.execute(update(MutationCandidateRow).where(MutationCandidateRow.candidate_hash.in_(mutation_hashes)).values(status="REVOKED_AUTHORITY"))
                promoted = list(
                    connection.execute(
                        select(FalsifierVersionRow.id).where(
                            FalsifierVersionRow.spec_hash.in_(mutation_hashes),
                            FalsifierVersionRow.lifecycle_state == "PROMOTE",
                        )
                    ).scalars()
                )
                if promoted:
                    connection.execute(update(FalsifierVersionRow).where(FalsifierVersionRow.id.in_(promoted)).values(lifecycle_state="REVOKED_AUTHORITY"))
                    counts["promotions"] = len(promoted)
                counts["mutations"] = len(mutation_hashes)

        germinal = connection.execute(select(ReceiptGerminalOutcomeRow.receipt_hash).where(ReceiptGerminalOutcomeRow.receipt_hash == receipt_hash)).scalar_one_or_none()
        if germinal is not None:
            connection.execute(update(ReceiptGerminalOutcomeRow).where(ReceiptGerminalOutcomeRow.receipt_hash == receipt_hash).values(status="REVOKED_AUTHORITY"))
            counts["germinal"] = 1
    return counts
