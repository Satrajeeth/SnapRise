"""add board templates

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-11 23:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('board_templates',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.String(length=1024), nullable=True),
    sa.Column('owner_user_id', sa.UUID(), nullable=False),
    sa.Column('is_public', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_board_templates_name'), 'board_templates', ['name'], unique=False)
    op.create_index(op.f('ix_board_templates_owner_user_id'), 'board_templates', ['owner_user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_board_templates_owner_user_id'), table_name='board_templates')
    op.drop_index(op.f('ix_board_templates_name'), table_name='board_templates')
    op.drop_table('board_templates')
