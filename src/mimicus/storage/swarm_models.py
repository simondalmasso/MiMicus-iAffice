from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from mimicus.storage.models import Base


class VerificationReceiptRow(Base):
    __tablename__ = "verification_receipts"
    receipt_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    receipt_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    origin_key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    # Rejected receipts are intentionally retained too, so these are hash-bound
    # identifiers rather than relational FKs. Accepted receipts are validated
    # against persisted run/claim rows before insertion.
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    claim_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    verified_status: Mapped[str] = mapped_column(String(32), nullable=False)
    authority_class: Mapped[str] = mapped_column(String(64), nullable=False)
    verifier_id: Mapped[str] = mapped_column(String(256), nullable=False)
    source_cluster: Mapped[str] = mapped_column(String(256), nullable=False)
    accepted: Mapped[int] = mapped_column(Integer, nullable=False)
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)


class ReceiptAttributionRow(Base):
    __tablename__ = "receipt_attributions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    receipt_hash: Mapped[str] = mapped_column(ForeignKey("verification_receipts.receipt_hash"), nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(128), nullable=False)
    capability: Mapped[str] = mapped_column(String(64), nullable=False)
    test_family: Mapped[str] = mapped_column(String(128), nullable=False)
    outcome: Mapped[int] = mapped_column(Integer, nullable=False)
    predicted_probability: Mapped[float] = mapped_column(Float, nullable=False)
    cost_contribution: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    decisive_test_contribution: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    __table_args__ = (UniqueConstraint("receipt_hash", "fingerprint", "capability", "test_family", name="uq_receipt_attribution"),)


class PairwiseCofailureRow(Base):
    __tablename__ = "pairwise_cofailure"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_a: Mapped[str] = mapped_column(String(64), nullable=False)
    agent_b: Mapped[str] = mapped_column(String(64), nullable=False)
    domain: Mapped[str] = mapped_column(String(128), nullable=False)
    capability: Mapped[str] = mapped_column(String(64), nullable=False)
    verified_episodes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cofailures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    independent_successes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False)
    __table_args__ = (UniqueConstraint("agent_a", "agent_b", "domain", "capability", name="uq_pairwise_cofailure"),)


class PairEpisodeRow(Base):
    __tablename__ = "pair_episode_updates"
    episode_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)


class AgentMarginalValueRow(Base):
    __tablename__ = "agent_marginal_value"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    domain: Mapped[str] = mapped_column(String(128), nullable=False)
    capability: Mapped[str] = mapped_column(String(64), nullable=False)
    verified_episodes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    successes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    marginal_sum: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cost_sum: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    decisive_test_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False)
    __table_args__ = (UniqueConstraint("fingerprint", "domain", "capability", name="uq_agent_marginal_value"),)


class ReceiptGerminalOutcomeRow(Base):
    __tablename__ = "receipt_germinal_outcomes"
    receipt_hash: Mapped[str] = mapped_column(ForeignKey("verification_receipts.receipt_hash"), primary_key=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)
