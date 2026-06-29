"""add_board_invitations_and_lead_outbox

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-06-30 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # `boardrole` already exists (created by the board_members migration); only
    # the new invitationstatus type needs creating. The DO/EXCEPTION guard makes
    # this idempotent so a partially-applied DB doesn't blow up on re-run.
    op.execute(
        "DO $$ BEGIN CREATE TYPE invitationstatus AS ENUM "
        "('pending', 'accepted', 'expired', 'revoked'); "
        "EXCEPTION WHEN duplicate_object THEN null; END $$;"
    )

    # create_type=False: the types already exist (see above / board_members),
    # so SQLAlchemy must reference them, not try to CREATE them again.
    boardrole = postgresql.ENUM('owner', 'editor', 'viewer', name='boardrole', create_type=False)
    invitationstatus = postgresql.ENUM(
        'pending', 'accepted', 'expired', 'revoked', name='invitationstatus', create_type=False
    )

    op.create_table(
        'board_invitations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('board_id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(length=320), nullable=False),
        sa.Column('role', boardrole, nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('status', invitationstatus, nullable=False),
        sa.Column('invited_by', sa.UUID(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['board_id'], ['boards.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_board_invitations_board_id'), 'board_invitations', ['board_id'], unique=False)
    op.create_index(op.f('ix_board_invitations_email'), 'board_invitations', ['email'], unique=False)
    op.create_index(op.f('ix_board_invitations_status'), 'board_invitations', ['status'], unique=False)
    # Unique: a token hash identifies exactly one invitation at accept time.
    op.create_index(op.f('ix_board_invitations_token_hash'), 'board_invitations', ['token_hash'], unique=True)

    op.create_table(
        'lead_outbox',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(length=320), nullable=False),
        sa.Column('source', sa.String(length=64), server_default='board_invite', nullable=False),
        sa.Column('board_id', sa.UUID(), nullable=True),
        sa.Column('invited_by', sa.UUID(), nullable=True),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('delivered', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_lead_outbox_email'), 'lead_outbox', ['email'], unique=False)
    op.create_index(op.f('ix_lead_outbox_delivered'), 'lead_outbox', ['delivered'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_lead_outbox_delivered'), table_name='lead_outbox')
    op.drop_index(op.f('ix_lead_outbox_email'), table_name='lead_outbox')
    op.drop_table('lead_outbox')

    op.drop_index(op.f('ix_board_invitations_token_hash'), table_name='board_invitations')
    op.drop_index(op.f('ix_board_invitations_status'), table_name='board_invitations')
    op.drop_index(op.f('ix_board_invitations_email'), table_name='board_invitations')
    op.drop_index(op.f('ix_board_invitations_board_id'), table_name='board_invitations')
    op.drop_table('board_invitations')

    # Leave the boardrole type in place (shared with board_members); only drop
    # the type this migration introduced.
    op.execute("DROP TYPE IF EXISTS invitationstatus")
