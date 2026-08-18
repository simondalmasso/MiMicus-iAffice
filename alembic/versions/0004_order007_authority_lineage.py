"""ORDER-007 verifier authority and counterfactual attribution state.

Revision ID: 0004_order007
Revises: 0003_order006
Create Date: 2026-08-18
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

import mimicus.storage.swarm_models  # noqa: F401
from mimicus.storage.models import Base

revision: str = "0004_order007"
down_revision: str | None = "0003_order006"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def _add_column_if_missing(table: str, column: sa.Column[object]) -> None:
    bind = op.get_bind()
    existing = {row["name"] for row in sa.inspect(bind).get_columns(table)}
    if column.name not in existing:
        op.add_column(table, column)


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.tables["verifier_authorities"].create(bind=bind, checkfirst=True)
    Base.metadata.tables["removal_attributions"].create(bind=bind, checkfirst=True)
    _add_column_if_missing("verification_receipts", sa.Column("verification_method", sa.String(length=64), nullable=True))
    _add_column_if_missing("verification_receipts", sa.Column("verifier_policy_hash", sa.String(length=64), nullable=True))
    _add_column_if_missing("verification_receipts", sa.Column("learning_active", sa.Integer(), nullable=False, server_default="0"))
    _add_column_if_missing("verification_receipts", sa.Column("superseded_by_hash", sa.String(length=64), nullable=True))


def downgrade() -> None:
    # Authority and adjudication history are intentionally non-destructive.
    pass
