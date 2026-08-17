"""ORDER-003 persistent swarm runtime state.

Revision ID: 0002_order003
Revises: 0001_order002
Create Date: 2026-08-17
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

from mimicus.storage.models import Base

revision: str = "0002_order003"
down_revision: str | None = "0001_order002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def _add_column_if_missing(table: str, column: sa.Column[object]) -> None:
    bind = op.get_bind()
    columns = {row["name"] for row in inspect(bind).get_columns(table)}
    if column.name not in columns:
        op.add_column(table, column)


def upgrade() -> None:
    bind = op.get_bind()
    # ORDER-002's initial migration used Base.metadata.create_all. On a clean DB it
    # therefore sees the current model and already creates these tables/columns.
    # checkfirst + introspection keeps this forward migration valid for both a real
    # ORDER-002 database and a clean database upgraded through the full chain.
    for name in ["agent_lineages", "agent_lineage_members", "falsifier_performance", "memory_transitions"]:
        Base.metadata.tables[name].create(bind=bind, checkfirst=True)

    _add_column_if_missing("agent_domain_calibration", sa.Column("last_verified_at", sa.String(length=64), nullable=True))
    _add_column_if_missing("agent_bankruptcy", sa.Column("updated_at", sa.String(length=64), nullable=True))
    _add_column_if_missing("coalitions", sa.Column("plan_hash", sa.String(length=64), nullable=True))
    _add_column_if_missing("coalitions", sa.Column("plan_json", sa.Text(), nullable=True))
    _add_column_if_missing("communications", sa.Column("provider_call_id", sa.String(length=128), nullable=True))
    _add_column_if_missing("communications", sa.Column("input_hash", sa.String(length=64), nullable=True))
    _add_column_if_missing("communications", sa.Column("output_hash", sa.String(length=64), nullable=True))
    _add_column_if_missing("communications", sa.Column("payload_json", sa.Text(), nullable=True))
    _add_column_if_missing("falsifier_specs", sa.Column("domain", sa.String(length=128), nullable=True))
    _add_column_if_missing("falsifier_versions", sa.Column("created_at", sa.String(length=64), nullable=True))
    _add_column_if_missing("mutation_candidates", sa.Column("spec_json", sa.Text(), nullable=True))
    _add_column_if_missing("mutation_candidates", sa.Column("evasion_hash", sa.String(length=64), nullable=True))
    _add_column_if_missing("memory_items", sa.Column("updated_at", sa.String(length=64), nullable=True))


def downgrade() -> None:
    # Intentionally non-destructive. ORDER-003 carries authority-bearing lineage,
    # immune-memory and germinal provenance that must not be silently erased.
    pass
