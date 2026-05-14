"""add_wip_limit_to_columns

Revision ID: 887766554433
Revises: f186e8eb62d8
Create Date: 2026-05-05 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '887766554433'
down_revision: Union[str, None] = 'f186e8eb62d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('columns', sa.Column('wip_limit', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('columns', 'wip_limit')
