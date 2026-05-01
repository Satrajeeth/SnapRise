"""Add SendGrid provider configuration.

Revision ID: 002_add_sendgrid_provider
Revises: 001_initial_schema
Create Date: 2026-05-01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "002_add_sendgrid_provider"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Insert SendGrid provider config into provider_config table
    op.execute(
        """
        INSERT INTO provider_config (
            provider_id,
            tier,
            enabled,
            weight,
            priority,
            daily_limit,
            monthly_limit,
            settings_json,
            created_at
        ) VALUES (
            'sendgrid',
            'fallback',
            true,
            1,
            100,
            0,
            0,
            '{"adapter": "app.providers.adapters.SendGridEmailProvider", "api_key": "", "from_email": ""}'::jsonb,
            CURRENT_TIMESTAMP
        ) ON CONFLICT (provider_id) DO NOTHING;
        """
    )


def downgrade() -> None:
    # Remove SendGrid provider config
    op.execute("DELETE FROM provider_config WHERE provider_id = 'sendgrid';")
