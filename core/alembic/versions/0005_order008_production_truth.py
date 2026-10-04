"""ORDER-008 production truth and decision-bound attribution state.

Revision ID: 0005_order008
Revises: 0004_order007
Create Date: 2026-08-19
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

import mimicus.storage.swarm_models  # noqa: F401
from alembic import op

revision: str = "0005_order008"
down_revision: str | None = "0004_order007"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def _add_column_if_missing(table: str, column: sa.Column[object]) -> None:
    bind = op.get_bind()
    existing = {row["name"] for row in sa.inspect(bind).get_columns(table)}
    if column.name not in existing:
        op.add_column(table, column)


def upgrade() -> None:
    _add_column_if_missing("removal_attributions", sa.Column("original_marginal_delta", sa.Float(), nullable=True))
    _add_column_if_missing("removal_attributions", sa.Column("decision_before_hash", sa.String(length=64), nullable=True))
    _add_column_if_missing("removal_attributions", sa.Column("decision_without_hash", sa.String(length=64), nullable=True))
    _add_column_if_missing("removal_attributions", sa.Column("verified_scope_json", sa.Text(), nullable=True))
    _add_column_if_missing("removal_attributions", sa.Column("active", sa.Integer(), nullable=False, server_default="1"))


def downgrade() -> None:
    # Verified attribution history is intentionally non-destructive.
    pass
