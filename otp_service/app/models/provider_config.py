import uuid
from sqlalchemy import (
    Column,
    String,
    Boolean,
    Integer,
    DateTime,
    JSON,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from app.db import Base


class ProviderConfig(Base):
    __tablename__ = "provider_configs"

    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    provider_name = Column(
        String(50),
        nullable=False,
        unique=True,
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    config_data = Column(
        JSON,
        nullable=False,
    )

    retry_strategy = Column(
        String(50),  # exponential / linear / fixed
        nullable=True,
    )

    max_retries = Column(
        Integer,
        nullable=False,
        default=3,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
    )