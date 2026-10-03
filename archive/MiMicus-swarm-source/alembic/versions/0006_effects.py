"""Mimicus effect authorization boundary.

Revision ID: 0006_effects
Revises: 0005_order008
Create Date: 2026-10-03
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_effects"
down_revision: str | None = "0005_order008"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "effect_approvals" not in tables:
        op.create_table(
            "effect_approvals",
            sa.Column("approval_id", sa.String(length=128), primary_key=True),
            sa.Column("envelope_hash", sa.String(length=64), nullable=False),
            sa.Column("approver_id", sa.String(length=256), nullable=False),
            sa.Column("issued_at", sa.String(length=64), nullable=False),
            sa.Column("expires_at", sa.String(length=64), nullable=False),
            sa.Column("consumed_at", sa.String(length=64), nullable=True),
            sa.Column("policy_version", sa.String(length=128), nullable=False),
        )
        op.create_index("ix_effect_approvals_envelope_hash", "effect_approvals", ["envelope_hash"])
        op.create_index("ix_effect_approvals_expires_at", "effect_approvals", ["expires_at"])

    tables = set(sa.inspect(bind).get_table_names())
    if "effect_intents" not in tables:
        op.create_table(
            "effect_intents",
            sa.Column("intent_id", sa.String(length=64), primary_key=True),
            sa.Column(
                "approval_id",
                sa.String(length=128),
                sa.ForeignKey("effect_approvals.approval_id"),
                nullable=False,
                unique=True,
            ),
            sa.Column("envelope_hash", sa.String(length=64), nullable=False),
            sa.Column("state", sa.String(length=32), nullable=False),
            sa.Column("created_at", sa.String(length=64), nullable=False),
            sa.Column("completed_at", sa.String(length=64), nullable=True),
            sa.Column("outcome_hash", sa.String(length=64), nullable=True),
            sa.Column("error_class", sa.String(length=256), nullable=True),
        )
        op.create_index("ix_effect_intents_approval_id", "effect_intents", ["approval_id"])
        op.create_index("ix_effect_intents_envelope_hash", "effect_intents", ["envelope_hash"])
        op.create_index("ix_effect_intents_state", "effect_intents", ["state"])


def downgrade() -> None:
    # Authorization/effect evidence is intentionally non-destructive.
    pass
