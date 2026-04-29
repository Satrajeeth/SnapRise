"""Inital schema with OTP models

Revision ID: 6775152c17bc
Revises: 90a86e25251e
Create Date: 2026-03-04 01:23:11.752092

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6775152c17bc'
down_revision: Union[str, Sequence[str], None] = '90a86e25251e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
