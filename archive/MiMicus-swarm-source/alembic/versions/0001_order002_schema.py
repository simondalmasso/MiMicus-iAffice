"""ORDER-002 initial portable schema.

Revision ID: 0001_order002
Revises:
Create Date: 2026-08-17
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from mimicus.storage.models import Base

revision: str = "0001_order002"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
