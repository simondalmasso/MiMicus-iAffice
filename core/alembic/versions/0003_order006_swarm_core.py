"""ORDER-006 verified swarm learning state.

Revision ID: 0003_order006
Revises: 0002_order003
Create Date: 2026-08-18
"""

from __future__ import annotations

from collections.abc import Sequence

import mimicus.storage.swarm_models  # noqa: F401
from alembic import op
from mimicus.storage.models import Base

revision: str = "0003_order006"
down_revision: str | None = "0002_order003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    for name in [
        "verification_receipts",
        "receipt_attributions",
        "pairwise_cofailure",
        "pair_episode_updates",
        "agent_marginal_value",
        "receipt_germinal_outcomes",
    ]:
        Base.metadata.tables[name].create(bind=bind, checkfirst=True)


def downgrade() -> None:
    # Authority-bearing verification and learned swarm state are intentionally non-destructive.
    pass
