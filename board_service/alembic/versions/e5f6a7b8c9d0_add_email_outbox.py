"""add_email_outbox

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-06-30 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'email_outbox',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('to_email', sa.String(length=320), nullable=False),
        sa.Column('subject', sa.String(length=512), nullable=False),
        sa.Column('html', sa.Text(), nullable=False),
        sa.Column('text', sa.Text(), nullable=True),
        sa.Column('delivered', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('attempts', sa.Integer(), server_default='0', nullable=False),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_email_outbox_to_email'), 'email_outbox', ['to_email'], unique=False)
    op.create_index(op.f('ix_email_outbox_delivered'), 'email_outbox', ['delivered'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_email_outbox_delivered'), table_name='email_outbox')
    op.drop_index(op.f('ix_email_outbox_to_email'), table_name='email_outbox')
    op.drop_table('email_outbox')
