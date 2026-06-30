from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.domain.enums import ProviderTier
from app.models.provider_config import ProviderConfig
from app.providers.base import TransactionalEmailPayload
from app.services.routing import RoutingEngine, RoutingOutcome


class EmailService:
    """Sends free-form transactional email through the same provider routing
    (tier/priority/weight/health/quota/circuit-breaker + SMTP fallback) the OTP
    path uses. This is what lets board_service deliver invitation emails without
    owning any SMTP/provider code of its own.

    The send is synchronous like the OTP send: it returns success only when a
    provider actually accepted the message, so the caller (board's email-outbox
    drain) can mark a row delivered strictly on success and retry otherwise.
    """

    def __init__(self, settings: Settings, routing_engine: RoutingEngine):
        self.settings = settings
        self.routing_engine = routing_engine

    async def send_email(
        self,
        session: AsyncSession,
        *,
        to: str,
        subject: str,
        html: str,
        text: str | None = None,
        tenant_id: str = "default",
    ) -> tuple[RoutingOutcome, str]:
        request_id = str(uuid.uuid4())
        providers = await self._get_provider_configs(session)
        payload = TransactionalEmailPayload(
            request_id=request_id,
            to_email=to,
            subject=subject,
            html=html,
            text=text,
            tenant_id=tenant_id,
        )
        outcome = await self.routing_engine.dispatch_transactional(providers, payload)
        return outcome, request_id

    async def _get_provider_configs(self, session: AsyncSession) -> list[ProviderConfig]:
        result = await session.execute(
            select(ProviderConfig).where(ProviderConfig.enabled.is_(True))
        )
        providers = list(result.scalars().all())
        if self.settings.smtp_fallback_enabled:
            providers.append(self._default_smtp_provider_config())
        return providers

    def _default_smtp_provider_config(self) -> ProviderConfig:
        # Mirrors OtpService._default_smtp_provider_config so the SMTP fallback
        # (e.g. mailhog in dev) is available to transactional email too.
        return ProviderConfig(
            provider_id=self.settings.smtp_provider_id,
            tier=ProviderTier.fallback,
            enabled=True,
            weight=1,
            priority=10_000,
            daily_limit=0,
            monthly_limit=0,
            settings_json={
                "adapter": "app.providers.adapters.SmtpEmailProvider",
                "host": self.settings.smtp_host,
                "port": self.settings.smtp_port,
                "from_email": self.settings.smtp_from_email,
                "timeout_seconds": self.settings.smtp_timeout_seconds,
                "username": self.settings.smtp_username,
                "password": self.settings.smtp_password,
                "use_tls": self.settings.smtp_use_tls,
                "use_ssl": self.settings.smtp_use_ssl,
            },
        )
