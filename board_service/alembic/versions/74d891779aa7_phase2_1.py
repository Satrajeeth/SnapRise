"""Phase2.1 (consolidated — tables created by 998877665544)

Revision ID: 74d891779aa7
Revises: 887766554433
Create Date: 2026-05-15 23:56:01.905752

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '74d891779aa7'
down_revision: Union[str, None] = '887766554433'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # No-op: board_members and column_access tables are created by
    # migration 998877665544 (the other branch from 887766554433).
    # This migration is kept as a merge-point ancestor only.
    pass


def downgrade() -> None:
    # No-op: corresponding downgrade handled by 998877665544.
    pass
