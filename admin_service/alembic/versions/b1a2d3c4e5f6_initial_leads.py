"""initial leads schema

Revision ID: b1a2d3c4e5f6
Revises:
Create Date: 2026-06-30 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b1a2d3c4e5f6'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Idempotent CREATE TYPE (DO/EXCEPTION) so a partially-applied / re-run DB
    # doesn't error — same convention as board_service's enum migrations.
    op.execute(
        "DO $$ BEGIN CREATE TYPE leadsource AS ENUM ('board_invite', 'promotion'); "
        "EXCEPTION WHEN duplicate_object THEN null; END $$;"
    )
    op.execute(
        "DO $$ BEGIN CREATE TYPE leadstatus AS ENUM ('new', 'contacted', 'converted'); "
        "EXCEPTION WHEN duplicate_object THEN null; END $$;"
    )

    # create_type=False: we created the types by hand above, so the table-create
    # must reference them rather than emit another CREATE TYPE.
    leadsource = postgresql.ENUM('board_invite', 'promotion', name='leadsource', create_type=False)
    leadstatus = postgresql.ENUM('new', 'contacted', 'converted', name='leadstatus', create_type=False)

    op.create_table(
        'leads',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(length=320), nullable=False),
        sa.Column('source', leadsource, nullable=False),
        sa.Column('board_id', sa.UUID(), nullable=True),
        sa.Column('invited_by', sa.UUID(), nullable=True),
        sa.Column('status', leadstatus, server_default='new', nullable=False),
        sa.Column('notes', sa.String(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email', 'source', 'board_id', name='uq_leads_email_source_board'),
    )
    op.create_index(op.f('ix_leads_email'), 'leads', ['email'], unique=False)
    op.create_index(op.f('ix_leads_source'), 'leads', ['source'], unique=False)
    op.create_index(op.f('ix_leads_status'), 'leads', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_leads_status'), table_name='leads')
    op.drop_index(op.f('ix_leads_source'), table_name='leads')
    op.drop_index(op.f('ix_leads_email'), table_name='leads')
    op.drop_table('leads')
    op.execute("DROP TYPE IF EXISTS leadstatus")
    op.execute("DROP TYPE IF EXISTS leadsource")
