from __future__ import annotations

import hmac
import json
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, insert, select, update
from sqlalchemy.engine import Engine

from mimicus.canonical import canonical_json, sha256_obj
from mimicus.storage.swarm_models import (
    AgentMarginalValueRow,
    PairEpisodeRow,
    PairwiseCofailureRow,
    ReceiptAttributionRow,
    ReceiptGerminalOutcomeRow,
    RemovalAttributionRow,
    VerificationReceiptRow,
    VerifierAuthorityRow,
)
from mimicus.verification.models import (
    ACCEPTED_AUTHORITY_CLASSES,
    ACCEPTED_VERIFICATION_METHODS,
    VerificationReceipt,
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _token_hash(token: str) -> str:
    return sha256_obj({"verifier_auth_token": token})


class SwarmStateStore:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def register_verifier_authority(
        self,
        *,
        verifier_id: str,
        authority_class: str,
        source_cluster: str,
        verification_method: str,
        auth_token: str,
    ) -> dict[str, Any]:
        if authority_class not in ACCEPTED_AUTHORITY_CLASSES:
            raise ValueError("authority class is not eligible for verified learning")
        if verification_method not in ACCEPTED_VERIFICATION_METHODS:
            raise ValueError("unsupported verifier authentication method")
        if len(auth_token) < 16:
            raise ValueError("verifier credential must be at least 16 characters")
        token_hash = _token_hash(auth_token)
        material = {
            "verifier_id": verifier_id,
            "authority_class": authority_class,
            "source_cluster": source_cluster,
            "verification_method": verification_method,
            "token_hash": token_hash,
        }
        policy_hash = sha256_obj(material)
        with self.engine.begin() as connection:
            existing = connection.execute(
                select(
                    VerifierAuthorityRow.authority_class,
                    VerifierAuthorityRow.source_cluster,
                    VerifierAuthorityRow.verification_method,
                    VerifierAuthorityRow.token_hash,
                    VerifierAuthorityRow.policy_hash,
                    VerifierAuthorityRow.active,
                ).where(VerifierAuthorityRow.verifier_id == verifier_id)
            ).mappings().one_or_none()
            if existing is None:
                connection.execute(
                    insert(VerifierAuthorityRow).values(
                        verifier_id=verifier_id,
                        authority_class=authority_class,
                        source_cluster=source_cluster,
                        verification_method=verification_method,
                        token_hash=token_hash,
                        policy_hash=policy_hash,
                        active=1,
                        created_at=_now(),
                    )
                )
            else:
                if (
                    str(existing["authority_class"]) != authority_class
                    or str(existing["source_cluster"]) != source_cluster
                    or str(existing["verification_method"]) != verification_method
                    or str(existing["token_hash"]) != token_hash
                    or str(existing["policy_hash"]) != policy_hash
                ):
                    raise ValueError("verifier authority policy is immutable")
                if not bool(existing["active"]):
                    raise ValueError("verifier authority is inactive")
        return {
            "verifier_id": verifier_id,
            "authority_class": authority_class,
            "source_cluster": source_cluster,
            "verification_method": verification_method,
            "policy_hash": policy_hash,
            "active": True,
        }

    def authenticate_verifier(
        self,
        *,
        verifier_id: str,
        authority_class: str,
        source_cluster: str,
        auth_token: str | None,
    ) -> tuple[bool, str | None, dict[str, Any] | None]:
        with self.engine.connect() as connection:
            row = connection.execute(
                select(
                    VerifierAuthorityRow.authority_class,
                    VerifierAuthorityRow.source_cluster,
                    VerifierAuthorityRow.verification_method,
                    VerifierAuthorityRow.token_hash,
                    VerifierAuthorityRow.policy_hash,
                    VerifierAuthorityRow.active,
                ).where(VerifierAuthorityRow.verifier_id == verifier_id)
            ).mappings().one_or_none()
        if row is None:
            return False, "verifier_not_authorized", None
        policy = {
            "verifier_id": verifier_id,
            "authority_class": str(row["authority_class"]),
            "source_cluster": str(row["source_cluster"]),
            "verification_method": str(row["verification_method"]),
            "policy_hash": str(row["policy_hash"]),
            "active": bool(row["active"]),
        }
        if not policy["active"]:
            return False, "verifier_policy_inactive", policy
        if authority_class != policy["authority_class"]:
            return False, "authority_class_policy_mismatch", policy
        if source_cluster != policy["source_cluster"]:
            return False, "source_cluster_policy_mismatch", policy
        if auth_token is None or not hmac.compare_digest(str(row["token_hash"]), _token_hash(auth_token)):
            return False, "verifier_authentication_failed", policy
        return True, None, policy

    def verifier_policies(self) -> list[dict[str, Any]]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                select(
                    VerifierAuthorityRow.verifier_id,
                    VerifierAuthorityRow.authority_class,
                    VerifierAuthorityRow.source_cluster,
                    VerifierAuthorityRow.verification_method,
                    VerifierAuthorityRow.policy_hash,
                    VerifierAuthorityRow.active,
                    VerifierAuthorityRow.created_at,
                ).order_by(VerifierAuthorityRow.verifier_id)
            ).mappings().all()
        return [dict(row) for row in rows]

    def receipt_by_origin(self, origin_key_hash: str) -> dict[str, Any] | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                select(
                    VerificationReceiptRow.payload_json,
                    VerificationReceiptRow.learning_active,
                    VerificationReceiptRow.superseded_by_hash,
                ).where(VerificationReceiptRow.origin_key_hash == origin_key_hash)
            ).mappings().one_or_none()
        if row is None:
            return None
        return json.loads(str(row["payload_json"])) | {
            "learning_active": bool(row["learning_active"]),
            "superseded_by_hash": row["superseded_by_hash"],
        }

    def receipt_payload(self, receipt_hash: str) -> dict[str, Any] | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                select(
                    VerificationReceiptRow.payload_json,
                    VerificationReceiptRow.learning_active,
                    VerificationReceiptRow.superseded_by_hash,
                ).where(VerificationReceiptRow.receipt_hash == receipt_hash)
            ).mappings().one_or_none()
        if row is None:
            return None
        return json.loads(str(row["payload_json"])) | {
            "learning_active": bool(row["learning_active"]),
            "superseded_by_hash": row["superseded_by_hash"],
        }

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
                    verification_method=receipt.verification_method,
                    verifier_policy_hash=receipt.verifier_policy_hash,
                    accepted=int(receipt.accepted),
                    learning_active=int(receipt.accepted),
                    superseded_by_hash=None,
                    rejection_reason=receipt.rejection_reason,
                    payload_json=receipt.model_dump_json(),
                    created_at=receipt.created_at.isoformat(),
                )
            )
        return True

    def deactivate_receipt(self, receipt_hash: str, superseded_by_hash: str) -> bool:
        with self.engine.begin() as connection:
            current = connection.execute(
                select(VerificationReceiptRow.learning_active).where(VerificationReceiptRow.receipt_hash == receipt_hash)
            ).scalar_one_or_none()
            if current is None or not bool(current):
                return False
            connection.execute(
                update(VerificationReceiptRow)
                .where(VerificationReceiptRow.receipt_hash == receipt_hash)
                .values(learning_active=0, superseded_by_hash=superseded_by_hash)
            )
        return True

    def receipts_for_run(self, run_id: str) -> list[dict[str, Any]]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                select(
                    VerificationReceiptRow.payload_json,
                    VerificationReceiptRow.learning_active,
                    VerificationReceiptRow.superseded_by_hash,
                ).where(VerificationReceiptRow.run_id == run_id).order_by(VerificationReceiptRow.created_at)
            ).mappings().all()
        return [
            json.loads(str(row["payload_json"]))
            | {"learning_active": bool(row["learning_active"]), "superseded_by_hash": row["superseded_by_hash"]}
            for row in rows
        ]

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
        return True

    def record_removal_attribution(
        self,
        *,
        receipt: VerificationReceipt,
        fingerprint: str,
        domain: str,
        capability: str,
        baseline_utility: float,
        without_agent_utility: float,
        marginal_delta: float,
        provenance_hash: str,
    ) -> bool:
        with self.engine.begin() as connection:
            existing = connection.execute(
                select(RemovalAttributionRow.id).where(
                    RemovalAttributionRow.receipt_hash == receipt.receipt_hash,
                    RemovalAttributionRow.fingerprint == fingerprint,
                    RemovalAttributionRow.capability == capability,
                )
            ).scalar_one_or_none()
            if existing is not None:
                return False
            connection.execute(
                insert(RemovalAttributionRow).values(
                    receipt_hash=receipt.receipt_hash,
                    run_id=receipt.run_id,
                    fingerprint=fingerprint,
                    domain=domain,
                    capability=capability,
                    baseline_utility=baseline_utility,
                    without_agent_utility=without_agent_utility,
                    marginal_delta=marginal_delta,
                    method="leave_one_out_semantic_decision_v1",
                    provenance_hash=provenance_hash,
                    created_at=_now(),
                )
            )
        return True

    def verified_authority(self, fingerprint: str, domain: str, capability: str) -> dict[str, Any]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                select(ReceiptAttributionRow.outcome, ReceiptAttributionRow.predicted_probability)
                .join(VerificationReceiptRow, VerificationReceiptRow.receipt_hash == ReceiptAttributionRow.receipt_hash)
                .where(
                    VerificationReceiptRow.accepted == 1,
                    VerificationReceiptRow.learning_active == 1,
                    ReceiptAttributionRow.fingerprint == fingerprint,
                    ReceiptAttributionRow.domain == domain,
                    ReceiptAttributionRow.capability == capability,
                )
            ).all()
        attempts = len(rows)
        successes = sum(int(bool(row.outcome)) for row in rows)
        failures = attempts - successes
        trust = 0.5 if attempts < 3 else successes / max(1, attempts)
        return {"attempts": attempts, "successes": successes, "failures": failures, "trust": trust}

    def rebuild_learning(self) -> dict[str, int]:
        """Rebuild aggregates solely from active authenticated receipts.

        This makes supersession/appeal non-destructive but prevents stale receipt
        contributions from being double-counted.
        """
        with self.engine.begin() as connection:
            attrs = connection.execute(
                select(
                    ReceiptAttributionRow.receipt_hash,
                    ReceiptAttributionRow.run_id,
                    ReceiptAttributionRow.fingerprint,
                    ReceiptAttributionRow.domain,
                    ReceiptAttributionRow.capability,
                    ReceiptAttributionRow.outcome,
                    ReceiptAttributionRow.cost_contribution,
                    ReceiptAttributionRow.decisive_test_contribution,
                )
                .join(VerificationReceiptRow, VerificationReceiptRow.receipt_hash == ReceiptAttributionRow.receipt_hash)
                .where(VerificationReceiptRow.accepted == 1, VerificationReceiptRow.learning_active == 1)
            ).mappings().all()
            removals = connection.execute(
                select(
                    RemovalAttributionRow.receipt_hash,
                    RemovalAttributionRow.run_id,
                    RemovalAttributionRow.fingerprint,
                    RemovalAttributionRow.domain,
                    RemovalAttributionRow.capability,
                    RemovalAttributionRow.marginal_delta,
                )
                .join(VerificationReceiptRow, VerificationReceiptRow.receipt_hash == RemovalAttributionRow.receipt_hash)
                .where(VerificationReceiptRow.accepted == 1, VerificationReceiptRow.learning_active == 1)
            ).mappings().all()
            connection.execute(delete(PairEpisodeRow))
            connection.execute(delete(PairwiseCofailureRow))
            connection.execute(delete(AgentMarginalValueRow))

            raw_groups: dict[tuple[str, str, str], dict[str, Any]] = defaultdict(
                lambda: {"runs": set(), "successes": 0, "failures": 0, "cost": 0.0, "decisive": 0}
            )
            for row in attrs:
                key = (str(row["fingerprint"]), str(row["domain"]), str(row["capability"]))
                raw_groups[key]["runs"].add(str(row["run_id"]))
                raw_groups[key]["successes"] += int(bool(row["outcome"]))
                raw_groups[key]["failures"] += int(not bool(row["outcome"]))
                raw_groups[key]["cost"] += float(row["cost_contribution"])
                raw_groups[key]["decisive"] += int(row["decisive_test_contribution"])

            removal_groups: dict[tuple[str, str, str], dict[str, Any]] = defaultdict(lambda: {"runs": set(), "marginal": 0.0})
            for row in removals:
                key = (str(row["fingerprint"]), str(row["domain"]), str(row["capability"]))
                removal_groups[key]["runs"].add(str(row["run_id"]))
                removal_groups[key]["marginal"] += float(row["marginal_delta"])

            for key in sorted(set(raw_groups) | set(removal_groups)):
                fingerprint, domain, capability = key
                raw = raw_groups[key]
                removal = removal_groups[key]
                episodes = len(set(raw["runs"]) | set(removal["runs"]))
                connection.execute(
                    insert(AgentMarginalValueRow).values(
                        fingerprint=fingerprint,
                        domain=domain,
                        capability=capability,
                        verified_episodes=episodes,
                        successes=int(raw["successes"]),
                        failures=int(raw["failures"]),
                        marginal_sum=float(removal["marginal"]),
                        cost_sum=float(raw["cost"]),
                        decisive_test_count=int(raw["decisive"]),
                        updated_at=_now(),
                    )
                )

            per_episode: dict[tuple[str, str, str], dict[str, bool]] = defaultdict(dict)
            for row in attrs:
                key = (str(row["run_id"]), str(row["domain"]), str(row["capability"]))
                fp = str(row["fingerprint"])
                per_episode[key][fp] = per_episode[key].get(fp, True) and bool(row["outcome"])
            pair_acc: dict[tuple[str, str, str, str], dict[str, int]] = defaultdict(lambda: {"episodes": 0, "cofailures": 0, "independent": 0})
            pair_updates = 0
            for (run_id, domain, capability), outcomes in sorted(per_episode.items()):
                fps = sorted(outcomes)
                for index, left in enumerate(fps):
                    for right in fps[index + 1 :]:
                        a, b = left, right
                        left_outcome, right_outcome = outcomes[a], outcomes[b]
                        key = (a, b, domain, capability)
                        pair_acc[key]["episodes"] += 1
                        pair_acc[key]["cofailures"] += int(not left_outcome and not right_outcome)
                        pair_acc[key]["independent"] += int(left_outcome != right_outcome)
                        episode_hash = sha256_obj({"run_id": run_id, "agents": (a, b), "domain": domain, "capability": capability})
                        connection.execute(insert(PairEpisodeRow).values(episode_hash=episode_hash, created_at=_now()))
                        pair_updates += 1
            for (a, b, domain, capability), values in sorted(pair_acc.items()):
                connection.execute(
                    insert(PairwiseCofailureRow).values(
                        agent_a=a,
                        agent_b=b,
                        domain=domain,
                        capability=capability,
                        verified_episodes=values["episodes"],
                        cofailures=values["cofailures"],
                        independent_successes=values["independent"],
                        updated_at=_now(),
                    )
                )
        return {"active_attributions": len(attrs), "active_removals": len(removals), "pair_updates": pair_updates}

    def update_pair_learning_for_run(self, run_id: str) -> int:
        del run_id
        return self.rebuild_learning()["pair_updates"]

    def signals(self, fingerprints: list[str], domain: str, capabilities: tuple[str, ...]) -> tuple[dict[str, dict[str, float]], dict[str, dict[str, float]]]:
        pair: dict[str, dict[str, float]] = {fp: {} for fp in fingerprints}
        marginal: dict[str, dict[str, float]] = {fp: {} for fp in fingerprints}
        with self.engine.connect() as connection:
            pair_rows = connection.execute(
                select(
                    PairwiseCofailureRow.agent_a,
                    PairwiseCofailureRow.agent_b,
                    PairwiseCofailureRow.verified_episodes,
                    PairwiseCofailureRow.cofailures,
                ).where(PairwiseCofailureRow.domain == domain, PairwiseCofailureRow.capability.in_(list(capabilities)))
            ).mappings().all()
            for pair_row in pair_rows:
                agent_a = str(pair_row["agent_a"])
                agent_b = str(pair_row["agent_b"])
                if agent_a not in pair or agent_b not in pair:
                    continue
                episodes = int(pair_row["verified_episodes"])
                confidence = episodes / (episodes + 5.0)
                penalty = (int(pair_row["cofailures"]) / max(1, episodes)) * confidence
                pair[agent_a][agent_b] = max(pair[agent_a].get(agent_b, 0.0), penalty)
                pair[agent_b][agent_a] = max(pair[agent_b].get(agent_a, 0.0), penalty)
            marginal_rows = connection.execute(
                select(
                    AgentMarginalValueRow.fingerprint,
                    AgentMarginalValueRow.capability,
                    AgentMarginalValueRow.marginal_sum,
                    AgentMarginalValueRow.verified_episodes,
                ).where(AgentMarginalValueRow.domain == domain, AgentMarginalValueRow.fingerprint.in_(fingerprints))
            ).mappings().all()
            for marginal_row in marginal_rows:
                capability = str(marginal_row["capability"])
                if capability not in capabilities:
                    continue
                fingerprint = str(marginal_row["fingerprint"])
                marginal[fingerprint][capability] = max(
                    -1.0,
                    min(1.0, float(marginal_row["marginal_sum"]) / max(1.0, float(marginal_row["verified_episodes"]))),
                )
        return pair, marginal

    def prior_failure_modes(self, domain: str) -> tuple[str, ...]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                select(
                    AgentMarginalValueRow.capability,
                    AgentMarginalValueRow.verified_episodes,
                    AgentMarginalValueRow.failures,
                    AgentMarginalValueRow.successes,
                ).where(AgentMarginalValueRow.domain == domain)
            ).mappings().all()
        return tuple(sorted({str(row["capability"]) for row in rows if int(row["verified_episodes"]) >= 3 and int(row["failures"]) > int(row["successes"])}))

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
        pair_query = select(
            PairwiseCofailureRow.agent_a,
            PairwiseCofailureRow.agent_b,
            PairwiseCofailureRow.domain,
            PairwiseCofailureRow.capability,
            PairwiseCofailureRow.verified_episodes,
            PairwiseCofailureRow.cofailures,
        )
        marginal_query = select(
            AgentMarginalValueRow.fingerprint,
            AgentMarginalValueRow.domain,
            AgentMarginalValueRow.capability,
            AgentMarginalValueRow.verified_episodes,
            AgentMarginalValueRow.successes,
            AgentMarginalValueRow.failures,
            AgentMarginalValueRow.marginal_sum,
            AgentMarginalValueRow.cost_sum,
            AgentMarginalValueRow.decisive_test_count,
        )
        removal_query = select(
            RemovalAttributionRow.receipt_hash,
            RemovalAttributionRow.run_id,
            RemovalAttributionRow.fingerprint,
            RemovalAttributionRow.domain,
            RemovalAttributionRow.capability,
            RemovalAttributionRow.baseline_utility,
            RemovalAttributionRow.without_agent_utility,
            RemovalAttributionRow.marginal_delta,
            RemovalAttributionRow.method,
            RemovalAttributionRow.provenance_hash,
        ).join(VerificationReceiptRow, VerificationReceiptRow.receipt_hash == RemovalAttributionRow.receipt_hash).where(
            VerificationReceiptRow.accepted == 1,
            VerificationReceiptRow.learning_active == 1,
        )
        if domain is not None:
            pair_query = pair_query.where(PairwiseCofailureRow.domain == domain)
            marginal_query = marginal_query.where(AgentMarginalValueRow.domain == domain)
            removal_query = removal_query.where(RemovalAttributionRow.domain == domain)
        with self.engine.connect() as connection:
            pairs = connection.execute(pair_query).mappings().all()
            marginal = connection.execute(marginal_query).mappings().all()
            removals = connection.execute(removal_query).mappings().all()
        return {
            "pairwise_cofailure": [
                {
                    "agent_a": row["agent_a"],
                    "agent_b": row["agent_b"],
                    "domain": row["domain"],
                    "capability": row["capability"],
                    "verified_episodes": row["verified_episodes"],
                    "cofailures": row["cofailures"],
                    "confidence": int(row["verified_episodes"]) / (int(row["verified_episodes"]) + 5.0),
                }
                for row in pairs
            ],
            "marginal_value": [dict(row) for row in marginal],
            "removal_attributions": [dict(row) for row in removals],
            "verifier_policies": self.verifier_policies(),
        }
