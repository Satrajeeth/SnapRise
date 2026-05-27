"""add_board_member_and_column_access

Revision ID: 998877665544
Revises: 887766554433
Create Date: 2026-05-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '998877665544'
down_revision: Union[str, None] = '887766554433'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enums explicitly
    boardrole = postgresql.ENUM('owner', 'editor', 'viewer', name='boardrole')
    boardrole.create(op.get_bind(), checkfirst=True)
    accesstype = postgresql.ENUM('read', 'write', name='accesstype')
    accesstype.create(op.get_bind(), checkfirst=True)

    # Create board_members table
    op.create_table('board_members',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('board_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('role', sa.Enum('owner', 'editor', 'viewer', name='boardrole'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['board_id'], ['boards.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_board_members_board_id'), 'board_members', ['board_id'], unique=False)
    op.create_index(op.f('ix_board_members_user_id'), 'board_members', ['user_id'], unique=False)

    # Create column_access table
    op.create_table('column_access',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('column_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('role_restriction', sa.Enum('owner', 'editor', 'viewer', name='boardrole'), nullable=True),
        sa.Column('access_type', sa.Enum('read', 'write', name='accesstype'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['column_id'], ['columns.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_column_access_column_id'), 'column_access', ['column_id'], unique=False)
    op.create_index(op.f('ix_column_access_user_id'), 'column_access', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_column_access_user_id'), table_name='column_access')
    op.drop_index(op.f('ix_column_access_column_id'), table_name='column_access')
    op.drop_table('column_access')
    op.drop_index(op.f('ix_board_members_user_id'), table_name='board_members')
    op.drop_index(op.f('ix_board_members_board_id'), table_name='board_members')
    op.drop_table('board_members')
    
    # Drop enums
    postgresql.ENUM(name='accesstype').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='boardrole').drop(op.get_bind(), checkfirst=True)
