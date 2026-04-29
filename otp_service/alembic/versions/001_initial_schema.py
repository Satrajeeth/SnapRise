"""Initial OTP service schema.

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-04-30
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')

    otp_purpose = postgresql.ENUM(
        "email_verification",
        "password_reset",
        name="otp_purpose",
        create_type=False,
    )
    challenge_status = postgresql.ENUM(
        "pending",
        "sent",
        "queued",
        "verified",
        "expired",
        "blocked",
        name="challenge_status",
        create_type=False,
    )
    provider_tier = postgresql.ENUM(
        "free",
        "fallback",
        name="provider_tier",
        create_type=False,
    )
    attempt_result = postgresql.ENUM(
        "sent",
        "failed",
        "queued",
        name="attempt_result",
        create_type=False,
    )
    provider_error_type = postgresql.ENUM(
        "retryable",
        "non_retryable",
        "quota_exhausted",
        "auth_error",
        name="provider_error_type",
        create_type=False,
    )
    retry_job_status = postgresql.ENUM(
        "pending",
        "completed",
        "failed",
        name="retry_job_status",
        create_type=False,
    )
    provider_config_tier = postgresql.ENUM(
        "free",
        "fallback",
        name="provider_config_tier",
        create_type=False,
    )

    bind = op.get_bind()
    otp_purpose.create(bind, checkfirst=True)
    challenge_status.create(bind, checkfirst=True)
    provider_tier.create(bind, checkfirst=True)
    attempt_result.create(bind, checkfirst=True)
    provider_error_type.create(bind, checkfirst=True)
    retry_job_status.create(bind, checkfirst=True)
    provider_config_tier.create(bind, checkfirst=True)

    op.create_table(
        "otp_challenges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("purpose", otp_purpose, nullable=False),
        sa.Column("otp_hash", sa.String(length=255), nullable=False),
        sa.Column("salt", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", challenge_status, nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("resend_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_allowed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_id", sa.String(length=120), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_otp_challenges_tenant_id", "otp_challenges", ["tenant_id"])
    op.create_index("ix_otp_challenges_email", "otp_challenges", ["email"])
    op.create_index("ix_otp_challenges_purpose", "otp_challenges", ["purpose"])
    op.create_index("ix_otp_challenges_status", "otp_challenges", ["status"])
    op.create_index("ix_otp_challenges_expires_at", "otp_challenges", ["expires_at"])
    op.create_index("ix_otp_challenges_idempotency_key", "otp_challenges", ["idempotency_key"])

    op.create_table(
        "provider_config",
        sa.Column("provider_id", sa.String(length=120), primary_key=True),
        sa.Column("tier", provider_config_tier, nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("weight", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("daily_limit", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("monthly_limit", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("settings_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_provider_config_enabled", "provider_config", ["enabled"])
    op.create_index("ix_provider_config_tier", "provider_config", ["tier"])

    op.create_table(
        "otp_delivery_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("challenge_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_id", sa.String(length=120), nullable=False),
        sa.Column("tier", provider_tier, nullable=False),
        sa.Column("result", attempt_result, nullable=False),
        sa.Column("error_type", provider_error_type, nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["challenge_id"], ["otp_challenges.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_otp_delivery_attempts_challenge_id", "otp_delivery_attempts", ["challenge_id"])
    op.create_index("ix_otp_delivery_attempts_provider_id", "otp_delivery_attempts", ["provider_id"])
    op.create_index("ix_otp_delivery_attempts_result", "otp_delivery_attempts", ["result"])
    op.create_index("ix_otp_delivery_attempts_created_at", "otp_delivery_attempts", ["created_at"])

    op.create_table(
        "otp_retry_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("challenge_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", retry_job_status, nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["challenge_id"], ["otp_challenges.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_otp_retry_jobs_challenge_id", "otp_retry_jobs", ["challenge_id"])
    op.create_index("ix_otp_retry_jobs_status", "otp_retry_jobs", ["status"])
    op.create_index("ix_otp_retry_jobs_next_retry_at", "otp_retry_jobs", ["next_retry_at"])


def downgrade() -> None:
    op.drop_index("ix_otp_retry_jobs_next_retry_at", table_name="otp_retry_jobs")
    op.drop_index("ix_otp_retry_jobs_status", table_name="otp_retry_jobs")
    op.drop_index("ix_otp_retry_jobs_challenge_id", table_name="otp_retry_jobs")
    op.drop_table("otp_retry_jobs")

    op.drop_index("ix_otp_delivery_attempts_created_at", table_name="otp_delivery_attempts")
    op.drop_index("ix_otp_delivery_attempts_result", table_name="otp_delivery_attempts")
    op.drop_index("ix_otp_delivery_attempts_provider_id", table_name="otp_delivery_attempts")
    op.drop_index("ix_otp_delivery_attempts_challenge_id", table_name="otp_delivery_attempts")
    op.drop_table("otp_delivery_attempts")

    op.drop_index("ix_provider_config_tier", table_name="provider_config")
    op.drop_index("ix_provider_config_enabled", table_name="provider_config")
    op.drop_table("provider_config")

    op.drop_index("ix_otp_challenges_idempotency_key", table_name="otp_challenges")
    op.drop_index("ix_otp_challenges_expires_at", table_name="otp_challenges")
    op.drop_index("ix_otp_challenges_status", table_name="otp_challenges")
    op.drop_index("ix_otp_challenges_purpose", table_name="otp_challenges")
    op.drop_index("ix_otp_challenges_email", table_name="otp_challenges")
    op.drop_index("ix_otp_challenges_tenant_id", table_name="otp_challenges")
    op.drop_table("otp_challenges")

    bind = op.get_bind()
    postgresql.ENUM(name="provider_config_tier").drop(bind, checkfirst=True)
    postgresql.ENUM(name="retry_job_status").drop(bind, checkfirst=True)
    postgresql.ENUM(name="provider_error_type").drop(bind, checkfirst=True)
    postgresql.ENUM(name="attempt_result").drop(bind, checkfirst=True)
    postgresql.ENUM(name="provider_tier").drop(bind, checkfirst=True)
    postgresql.ENUM(name="challenge_status").drop(bind, checkfirst=True)
    postgresql.ENUM(name="otp_purpose").drop(bind, checkfirst=True)
