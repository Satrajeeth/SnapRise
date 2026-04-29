from sqlalchemy import Boolean, DateTime, Enum, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.domain.enums import ProviderTier


class ProviderConfig(Base):
    __tablename__ = "provider_config"

    provider_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    tier: Mapped[ProviderTier] = mapped_column(Enum(ProviderTier, name="provider_config_tier"), index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    weight: Mapped[int] = mapped_column(Integer, default=1)
    priority: Mapped[int] = mapped_column(Integer, default=100)
    daily_limit: Mapped[int] = mapped_column(Integer, default=0)
    monthly_limit: Mapped[int] = mapped_column(Integer, default=0)
    settings_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
