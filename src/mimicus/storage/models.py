from __future__ import annotations

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative root for the portable SQLite/PostgreSQL schema."""


class RunRow(Base):
    __tablename__ = "runs"
    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    config_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    ledger_head: Mapped[str] = mapped_column(String(64), nullable=False)
    result_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)


class EventRow(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    prev_event_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    event_json: Mapped[str] = mapped_column(Text, nullable=False)
    __table_args__ = (UniqueConstraint("run_id", "sequence", name="uq_events_run_sequence"),)


class TaskLedgerRow(Base):
    __tablename__ = "task_ledgers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.run_id"), unique=True, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class ProgressLedgerRow(Base):
    __tablename__ = "progress_ledgers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.run_id"), nullable=False, index=True)
    step: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    __table_args__ = (UniqueConstraint("run_id", "step", name="uq_progress_run_step"),)


class AgentFingerprintRow(Base):
    __tablename__ = "agent_fingerprints"
    fingerprint: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    manifest_json: Mapped[str] = mapped_column(Text, nullable=False)


class AgentDomainCalibrationRow(Base):
    __tablename__ = "agent_domain_calibration"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fingerprint: Mapped[str] = mapped_column(ForeignKey("agent_fingerprints.fingerprint"), nullable=False)
    domain: Mapped[str] = mapped_column(String(128), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    successes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    brier_sum: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    canary_failure_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    __table_args__ = (UniqueConstraint("fingerprint", "domain", name="uq_calibration_fp_domain"),)


class AgentBankruptcyRow(Base):
    __tablename__ = "agent_bankruptcy"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fingerprint: Mapped[str] = mapped_column(ForeignKey("agent_fingerprints.fingerprint"), nullable=False)
    domain: Mapped[str] = mapped_column(String(128), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (UniqueConstraint("fingerprint", "domain", name="uq_bankruptcy_fp_domain"),)


class CoalitionRow(Base):
    __tablename__ = "coalitions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.run_id"), nullable=False, index=True)
    topology: Mapped[str] = mapped_column(String(64), nullable=False)
    members_json: Mapped[str] = mapped_column(Text, nullable=False)
    rationale_json: Mapped[str] = mapped_column(Text, nullable=False)


class CommunicationRow(Base):
    __tablename__ = "communications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.run_id"), nullable=False, index=True)
    round_no: Mapped[int] = mapped_column(Integer, nullable=False)
    source_fp: Mapped[str] = mapped_column(String(64), nullable=False)
    target_fp: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)


class ClaimRow(Base):
    __tablename__ = "claims"
    claim_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.run_id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class EvidenceRow(Base):
    __tablename__ = "evidence"
    evidence_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.run_id"), nullable=False, index=True)
    independence_cluster: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class FalsifierSpecRow(Base):
    __tablename__ = "falsifier_specs"
    spec_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    spec_id: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    primitive: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    parent_hash: Mapped[str | None] = mapped_column(String(64))
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    __table_args__ = (UniqueConstraint("spec_id", "version", name="uq_falsifier_id_version"),)


class FalsifierVersionRow(Base):
    __tablename__ = "falsifier_versions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    spec_hash: Mapped[str] = mapped_column(ForeignKey("falsifier_specs.spec_hash"), nullable=False)
    lifecycle_state: Mapped[str] = mapped_column(String(32), nullable=False)
    decision_json: Mapped[str] = mapped_column(Text, nullable=False)


class FalsifierExecutionRow(Base):
    __tablename__ = "falsifier_executions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.run_id"), nullable=False, index=True)
    spec_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    verdict: Mapped[str] = mapped_column(String(32), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class EvasionEventRow(Base):
    __tablename__ = "evasion_events"
    evasion_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    parent_spec_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    ground_truth_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class FossilClaimRow(Base):
    __tablename__ = "fossil_claims"
    fossil_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    primitive: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    expected_verdict: Mapped[str] = mapped_column(String(32), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class MutationCandidateRow(Base):
    __tablename__ = "mutation_candidates"
    candidate_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    parent_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    metrics_json: Mapped[str] = mapped_column(Text, nullable=False)


class MemoryItemRow(Base):
    __tablename__ = "memory_items"
    memory_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    claim_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    authority: Mapped[float] = mapped_column(Float, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class MemoryLinkRow(Base):
    __tablename__ = "memory_links"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parent_memory_id: Mapped[str] = mapped_column(ForeignKey("memory_items.memory_id"), nullable=False)
    child_memory_id: Mapped[str] = mapped_column(ForeignKey("memory_items.memory_id"), nullable=False)
    relation: Mapped[str] = mapped_column(String(64), nullable=False)
    __table_args__ = (UniqueConstraint("parent_memory_id", "child_memory_id", "relation", name="uq_memory_link"),)


Index("ix_falsifier_execution_run_verdict", FalsifierExecutionRow.run_id, FalsifierExecutionRow.verdict)
