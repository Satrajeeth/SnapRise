"""Initial OTP service schema

Revision ID: 001_initial_schema
Revises:
Create Date: 02-03-2026
"""

from alembic import op
import sqlalchemy as sa 
from sqlalchemy.dialects import postgresql

revision = "001_initial_schema"
down_revision = None 
branch_label = None
depends_on = None

def upgrade():
    #Enable UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')

    #OTP Challenges 

    op.create_table(
        "otp_challenges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id",postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("otp_hash", sa.Text(), nullable=False),
        sa.Column('salt', sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, default=0),
        sa.Column("next_allowed_at",sa.DateTime()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("verified_at", sa.DateTime()),

    )

    op.create_index("ix_otp_challenges_lookup",
                    "otp_challenges",
                    ["tenant_id", "email", "purpose"],
    )
    
    op.create_index("ix_otp_challenges_expires",
                    "otp_challenges",
                    ["expires_at"],
    )

    #OTP DELIVERY ATTEMPTS

    op.create_table(
        "otp_delivery_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("challenge_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_id", sa.Text(), nullable=False),
        sa.Column("tier", sa.Text(), nullable=False),
        sa.Column("results", sa.Text(), nullable=False),
        sa.Column("error_type", sa.Text()),
        sa.Column("latency_ms", sa.Integer()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(
            ["challenge_id"],
            ["otp_challenges.id"],
            ondelete="CASCADE",
        ),
    )


    op.create_index(
        "ix_otp_delivery_attempts_challenge",
        "otp_delivery_attempts",
        ["challenge_id"],
    )


    #OTP RETRY JOBS

    op.create_table(
        "otp_retry_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("challenge_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0"),
        sa.Column("next_retry_at", sa.DateTime(), nullable=False),
        sa.Column("last_error", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(
            ["challenge_id"],
            ["otp_challenges.id"],
            ondelete="CASCADE",
        ),
    )


    op.create_index(
        "ix_otp_retry_jobs_challenge",
        "otp_retry_jobs",
        ["challenge_id"],
    )

    #PROVIDER CONFIG

    op.create_table(
        "provider_config",
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tier", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("weight", sa.Numeric(5, 2), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("daily_limit", sa.Integer(), nullable=False),
        sa.Column("monthly_limit", sa.Integer(), nullable=False),
        sa.Column("settings_json", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("daily_limit >= 0"),
        sa.CheckConstraint("monthly_limit >= 0"),
        sa.CheckConstraint("priority >= 0"),
        sa.CheckConstraint("weight > 0"),
    )

    #USER TABLE

    op.create_table(
        "user",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("hashed_password", sa.String(1024), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_superuser", sa.Boolean(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
    )

    op.create_index("ix_user_email", "user", ["email"], unique=True)

    def downgrade():
        op.drop_table("user")
        op.drop_table("provider_config")
        op.drop_table("otp_retry_jobs")
        op.drop_table("otp_delivery_attempts")
        op.drop_table("otp_challenges")