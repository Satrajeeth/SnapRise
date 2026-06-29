import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import EncryptionStatus, LifecycleStage


class Board(Base):
    __tablename__ = "boards"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    
    lifecycle_stage: Mapped[LifecycleStage] = mapped_column(
        Enum(LifecycleStage), default=LifecycleStage.ACTIVE, index=True
    )
    encryption_status: Mapped[EncryptionStatus] = mapped_column(
        Enum(EncryptionStatus), default=EncryptionStatus.DISABLED
    )

    # JSONB fields for dynamic data
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, server_default='{}')
    ai_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, server_default='{}')
    custom_fields: Mapped[dict] = mapped_column(JSONB, default=dict, server_default='{}')

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    columns: Mapped[List["Column"]] = relationship("Column", back_populates="board", cascade="all, delete-orphan")
    members: Mapped[List["BoardMember"]] = relationship("BoardMember", back_populates="board", cascade="all, delete-orphan")
    invitations: Mapped[List["BoardInvitation"]] = relationship("BoardInvitation", back_populates="board", cascade="all, delete-orphan")
