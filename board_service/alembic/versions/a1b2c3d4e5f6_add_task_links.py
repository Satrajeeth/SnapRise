"""add task links

Revision ID: a1b2c3d4e5f6
Revises: 74d891779aa7, 998877665544
Create Date: 2026-06-11 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = ('74d891779aa7', '998877665544')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure linktype enum exists
    op.execute("DO $$ BEGIN CREATE TYPE linktype AS ENUM ('blocks', 'is_blocked_by', 'relates_to'); EXCEPTION WHEN duplicate_object THEN null; END $$;")

    op.create_table('task_links',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('source_task_id', sa.UUID(), nullable=False),
    sa.Column('target_task_id', sa.UUID(), nullable=False),
    sa.Column('link_type', postgresql.ENUM('blocks', 'is_blocked_by', 'relates_to', name='linktype', create_type=False), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['source_task_id'], ['tasks.id'], ),
    sa.ForeignKeyConstraint(['target_task_id'], ['tasks.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_task_links_link_type'), 'task_links', ['link_type'], unique=False)
    op.create_index(op.f('ix_task_links_source_task_id'), 'task_links', ['source_task_id'], unique=False)
    op.create_index(op.f('ix_task_links_target_task_id'), 'task_links', ['target_task_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_task_links_target_task_id'), table_name='task_links')
    op.drop_index(op.f('ix_task_links_source_task_id'), table_name='task_links')
    op.drop_index(op.f('ix_task_links_link_type'), table_name='task_links')
    op.drop_table('task_links')
