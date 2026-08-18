from __future__ import annotations

from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, ConfigDict, Field, field_validator

from mimicus.canonical import sha256_obj

ACCEPTED_AUTHORITY_CLASSES = frozenset({"deterministic_oracle", "signed_registry", "trusted_human"})


class VerificationSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str = Field(min_length=1, max_length=64)
    claim_hash: str = Field(min_length=64, max_length=64)
    verified_status: str = Field(pattern="^(SUPPORTED|FALSIFIED)$")
    authority_class: str = Field(min_length=1, max_length=64)
    evidence_hashes: tuple[str, ...] = ()
    snapshot_hashes: tuple[str, ...] = ()
    verifier_id: str = Field(min_length=1, max_length=256)
    observed_at: datetime
    source_independence_cluster: str = Field(min_length=1, max_length=256)
    supersedes_receipt_hash: str | None = None
    appeal_of_receipt_hash: str | None = None

    @field_validator("evidence_hashes", "snapshot_hashes")
    @classmethod
    def validate_hashes(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(len(item) != 64 for item in value):
            raise ValueError("verification evidence/snapshot hashes must be sha256 hex-length")
        return value

    @property
    def origin_key_hash(self) -> str:
        """Deduplicate paraphrases from the same verifier/origin for one target.

        Evidence wording, snapshot ordering and observed timestamp are deliberately
        excluded so repeated reports cannot multiply authority. A formal
        supersession/appeal is a distinct origin key because it is an explicit
        immutable lineage operation.
        """
        return sha256_obj(
            {
                "run_id": self.run_id,
                "claim_hash": self.claim_hash,
                "verified_status": self.verified_status,
                "authority_class": self.authority_class,
                "verifier_id": self.verifier_id,
                "source_cluster": self.source_independence_cluster,
                "supersedes": self.supersedes_receipt_hash,
                "appeal_of": self.appeal_of_receipt_hash,
            }
        )


class VerificationReceipt(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    receipt_id: str
    receipt_hash: str
    origin_key_hash: str
    run_id: str
    claim_hash: str
    verified_status: str
    authority_class: str
    evidence_hashes: tuple[str, ...]
    snapshot_hashes: tuple[str, ...]
    verifier_id: str
    observed_at: datetime
    source_independence_cluster: str
    created_at: datetime
    supersedes_receipt_hash: str | None = None
    appeal_of_receipt_hash: str | None = None
    accepted: bool
    rejection_reason: str | None = None


def build_receipt(submission: VerificationSubmission, *, accepted: bool, rejection_reason: str | None = None) -> VerificationReceipt:
    created_at = datetime.now(UTC)
    receipt_id = str(uuid5(NAMESPACE_URL, f"mimicus-verification:{submission.origin_key_hash}"))
    material = submission.model_dump(mode="json") | {
        "receipt_id": receipt_id,
        "origin_key_hash": submission.origin_key_hash,
        "accepted": accepted,
        "rejection_reason": rejection_reason,
    }
    receipt_hash = sha256_obj(material)
    return VerificationReceipt(
        receipt_id=receipt_id,
        receipt_hash=receipt_hash,
        origin_key_hash=submission.origin_key_hash,
        run_id=submission.run_id,
        claim_hash=submission.claim_hash,
        verified_status=submission.verified_status,
        authority_class=submission.authority_class,
        evidence_hashes=tuple(sorted(set(submission.evidence_hashes))),
        snapshot_hashes=tuple(sorted(set(submission.snapshot_hashes))),
        verifier_id=submission.verifier_id,
        observed_at=submission.observed_at,
        source_independence_cluster=submission.source_independence_cluster,
        created_at=created_at,
        supersedes_receipt_hash=submission.supersedes_receipt_hash,
        appeal_of_receipt_hash=submission.appeal_of_receipt_hash,
        accepted=accepted,
        rejection_reason=rejection_reason,
    )
