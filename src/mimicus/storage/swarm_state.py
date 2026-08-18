from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import insert, select, update
from sqlalchemy.engine import Engine

from mimicus.canonical import canonical_json, sha256_obj
from mimicus.storage.swarm_models import (
    AgentMarginalValueRow,
    PairEpisodeRow,
    PairwiseCofailureRow,
    ReceiptAttributionRow,
    ReceiptGerminalOutcomeRow,
    VerificationReceiptRow,
)
from mimicus.verification.models import VerificationReceipt


def _now() -> str:
    return datetime.now(UTC).isoformat()


class SwarmStateStore:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def receipt_by_origin(self, origin_key_hash: str) -> dict[str, Any] | None:
        with self.engine.connect() as connection:
            payload = connection.execute(select(VerificationReceiptRow.payload_json).where(VerificationReceiptRow.origin_key_hash == origin_key_hash)).scalar_one_or_none()
        return None if payload is None else json.loads(payload)

    def persist_receipt(self, receipt: VerificationReceipt) -> bool:
        with self.engine.begin() as connection:
            existing = connection.execute(select(VerificationReceiptRow.receipt_hash).where(VerificationReceiptRow.origin_key_hash == receipt.origin_key_hash)).scalar_one_or_none()
            if existing is not None:
                return False
            connection.execute(
                insert(VerificationReceiptRow).values(
                    receipt_hash=receipt.receipt_hash,
                    receipt_id=receipt.receipt_id,
                    origin_key_hash=receipt.origin_key_hash,
                    run_id=receipt.run_id,
                    claim_hash=receipt.claim_hash,
                    verified_status=receipt.verified_status,
                    authority_class=receipt.authority_class,
                    verifier_id=receipt.verifier_id,
                    source_cluster=receipt.source_independence_cluster,
                    accepted=int(receipt.accepted),
                    rejection_reason=receipt.rejection_reason,
                    payload_json=receipt.model_dump_json(),
                    created_at=receipt.created_at.isoformat(),
                )
            )
        return True

    def receipts_for_run(self, run_id: str) -> list[dict[str, Any]]:
        with self.engine.connect() as connection:
            rows = (
                connection.execute(select(VerificationReceiptRow.payload_json).where(VerificationReceiptRow.run_id == run_id).order_by(VerificationReceiptRow.created_at))
                .scalars()
                .all()
            )
        return [json.loads(row) for row in rows]

    def receipt_exists(self, receipt_hash: str) -> bool:
        with self.engine.connect() as connection:
            return connection.execute(select(VerificationReceiptRow.receipt_hash).where(VerificationReceiptRow.receipt_hash == receipt_hash)).scalar_one_or_none() is not None

    def record_attribution(
        self,
        *,
        receipt: VerificationReceipt,
        fingerprint: str,
        domain: str,
        capability: str,
        test_family: str,
        outcome: bool,
        predicted_probability: float,
        cost_contribution: float,
        decisive_test_contribution: int,
    ) -> bool:
        with self.engine.begin() as connection:
            existing = connection.execute(
                select(ReceiptAttributionRow.id).where(
                    ReceiptAttributionRow.receipt_hash == receipt.receipt_hash,
                    ReceiptAttributionRow.fingerprint == fingerprint,
                    ReceiptAttributionRow.capability == capability,
                    ReceiptAttributionRow.test_family == test_family,
                )
            ).scalar_one_or_none()
            if existing is not None:
                return False
            connection.execute(
                insert(ReceiptAttributionRow).values(
                    receipt_hash=receipt.receipt_hash,
                    run_id=receipt.run_id,
                    fingerprint=fingerprint,
                    domain=domain,
                    capability=capability,
                    test_family=test_family,
                    outcome=int(outcome),
                    predicted_probability=predicted_probability,
                    cost_contribution=cost_contribution,
                    decisive_test_contribution=decisive_test_contribution,
                )
            )
            row_id = connection.execute(
                select(AgentMarginalValueRow.id).where(
                    AgentMarginalValueRow.fingerprint == fingerprint,
                    AgentMarginalValueRow.domain == domain,
                    AgentMarginalValueRow.capability == capability,
                )
            ).scalar_one_or_none()
            if row_id is None:
                connection.execute(
                    insert(AgentMarginalValueRow).values(
                        fingerprint=fingerprint,
                        domain=domain,
                        capability=capability,
                        verified_episodes=1,
                        successes=int(outcome),
                        failures=int(not outcome),
                        marginal_sum=1.0 if outcome else -1.0,
                        cost_sum=cost_contribution,
                        decisive_test_count=decisive_test_contribution,
                        updated_at=_now(),
                    )
                )
            else:
                current = connection.execute(select(AgentMarginalValueRow).where(AgentMarginalValueRow.id == row_id)).scalar_one()
                connection.execute(
                    update(AgentMarginalValueRow)
                    .where(AgentMarginalValueRow.id == row_id)
                    .values(
                        verified_episodes=current.verified_episodes + 1,
                        successes=current.successes + int(outcome),
                        failures=current.failures + int(not outcome),
                        marginal_sum=current.marginal_sum + (1.0 if outcome else -1.0),
                        cost_sum=current.cost_sum + cost_contribution,
                        decisive_test_count=current.decisive_test_count + decisive_test_contribution,
                        updated_at=_now(),
                    )
                )
        return True

    def update_pair_learning_for_run(self, run_id: str) -> int:
        with self.engine.begin() as connection:
            rows = connection.execute(
                select(
                    ReceiptAttributionRow.receipt_hash,
                    ReceiptAttributionRow.fingerprint,
                    ReceiptAttributionRow.domain,
                    ReceiptAttributionRow.capability,
                    ReceiptAttributionRow.outcome,
                ).where(ReceiptAttributionRow.run_id == run_id)
            ).all()
            updates = 0
            for index, left in enumerate(rows):
                for right in rows[index + 1 :]:
                    if left.fingerprint == right.fingerprint or left.domain != right.domain or left.capability != right.capability:
                        continue
                    a, b = sorted((left.fingerprint, right.fingerprint))
                    episode_hash = sha256_obj(
                        {
                            "receipts": sorted((left.receipt_hash, right.receipt_hash)),
                            "agents": (a, b),
                            "domain": left.domain,
                            "capability": left.capability,
                        }
                    )
                    if connection.execute(select(PairEpisodeRow.episode_hash).where(PairEpisodeRow.episode_hash == episode_hash)).scalar_one_or_none() is not None:
                        continue
                    connection.execute(insert(PairEpisodeRow).values(episode_hash=episode_hash, created_at=_now()))
                    row_id = connection.execute(
                        select(PairwiseCofailureRow.id).where(
                            PairwiseCofailureRow.agent_a == a,
                            PairwiseCofailureRow.agent_b == b,
                            PairwiseCofailureRow.domain == left.domain,
                            PairwiseCofailureRow.capability == left.capability,
                        )
                    ).scalar_one_or_none()
                    cofail = int(not bool(left.outcome) and not bool(right.outcome))
                    independent = int(bool(left.outcome) != bool(right.outcome))
                    if row_id is None:
                        connection.execute(
                            insert(PairwiseCofailureRow).values(
                                agent_a=a,
                                agent_b=b,
                                domain=left.domain,
                                capability=left.capability,
                                verified_episodes=1,
                                cofailures=cofail,
                                independent_successes=independent,
                                updated_at=_now(),
                            )
                        )
                    else:
                        current = connection.execute(select(PairwiseCofailureRow).where(PairwiseCofailureRow.id == row_id)).scalar_one()
                        connection.execute(
                            update(PairwiseCofailureRow)
                            .where(PairwiseCofailureRow.id == row_id)
                            .values(
                                verified_episodes=current.verified_episodes + 1,
                                cofailures=current.cofailures + cofail,
                                independent_successes=current.independent_successes + independent,
                                updated_at=_now(),
                            )
                        )
                    updates += 1
        return updates

    def signals(self, fingerprints: list[str], domain: str, capabilities: tuple[str, ...]) -> tuple[dict[str, dict[str, float]], dict[str, dict[str, float]]]:
        pair: dict[str, dict[str, float]] = {fp: {} for fp in fingerprints}
        marginal: dict[str, dict[str, float]] = {fp: {} for fp in fingerprints}
        with self.engine.connect() as connection:
            pair_rows = (
                connection.execute(select(PairwiseCofailureRow).where(PairwiseCofailureRow.domain == domain, PairwiseCofailureRow.capability.in_(list(capabilities))))
                .scalars()
                .all()
            )
            for pair_row in pair_rows:
                if pair_row.agent_a not in pair or pair_row.agent_b not in pair:
                    continue
                confidence = pair_row.verified_episodes / (pair_row.verified_episodes + 5.0)
                penalty = (pair_row.cofailures / max(1, pair_row.verified_episodes)) * confidence
                pair[pair_row.agent_a][pair_row.agent_b] = max(pair[pair_row.agent_a].get(pair_row.agent_b, 0.0), penalty)
                pair[pair_row.agent_b][pair_row.agent_a] = max(pair[pair_row.agent_b].get(pair_row.agent_a, 0.0), penalty)
            marginal_rows = (
                connection.execute(select(AgentMarginalValueRow).where(AgentMarginalValueRow.domain == domain, AgentMarginalValueRow.fingerprint.in_(fingerprints))).scalars().all()
            )
            for marginal_row in marginal_rows:
                if marginal_row.capability not in capabilities:
                    continue
                marginal[marginal_row.fingerprint][marginal_row.capability] = max(-1.0, min(1.0, marginal_row.marginal_sum / (marginal_row.verified_episodes + 4.0)))
        return pair, marginal

    def prior_failure_modes(self, domain: str) -> tuple[str, ...]:
        with self.engine.connect() as connection:
            rows = connection.execute(select(AgentMarginalValueRow).where(AgentMarginalValueRow.domain == domain)).scalars().all()
        return tuple(sorted({row.capability for row in rows if row.verified_episodes >= 3 and row.failures > row.successes}))

    def record_germinal_outcome(self, receipt_hash: str, status: str, payload: dict[str, Any]) -> None:
        with self.engine.begin() as connection:
            existing = connection.execute(select(ReceiptGerminalOutcomeRow.receipt_hash).where(ReceiptGerminalOutcomeRow.receipt_hash == receipt_hash)).scalar_one_or_none()
            if existing is None:
                connection.execute(
                    insert(ReceiptGerminalOutcomeRow).values(
                        receipt_hash=receipt_hash,
                        status=status,
                        payload_json=canonical_json(payload),
                        created_at=_now(),
                    )
                )

    def learned_state(self, domain: str | None = None) -> dict[str, Any]:
        with self.engine.connect() as connection:
            pairs = connection.execute(select(PairwiseCofailureRow)).scalars().all()
            marginal = connection.execute(select(AgentMarginalValueRow)).scalars().all()
        if domain is not None:
            pairs = [row for row in pairs if row.domain == domain]
            marginal = [row for row in marginal if row.domain == domain]
        return {
            "pairwise_cofailure": [
                {
                    "agent_a": row.agent_a,
                    "agent_b": row.agent_b,
                    "domain": row.domain,
                    "capability": row.capability,
                    "verified_episodes": row.verified_episodes,
                    "cofailures": row.cofailures,
                    "confidence": row.verified_episodes / (row.verified_episodes + 5.0),
                }
                for row in pairs
            ],
            "marginal_value": [
                {
                    "fingerprint": row.fingerprint,
                    "domain": row.domain,
                    "capability": row.capability,
                    "verified_episodes": row.verified_episodes,
                    "successes": row.successes,
                    "failures": row.failures,
                    "marginal_sum": row.marginal_sum,
                    "cost_sum": row.cost_sum,
                    "decisive_test_count": row.decisive_test_count,
                }
                for row in marginal
            ],
        }
