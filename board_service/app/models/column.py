import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Column(Base):
    __tablename__ = "columns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    board_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("boards.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    position: Mapped[int] = mapped_column(Integer, default=0)
    wip_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # JSONB fields for dynamic data
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, server_default='{}')
    ai_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, server_default='{}')

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    board: Mapped["Board"] = relationship("Board", back_populates="columns")
    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="column", cascade="all, delete-orphan")
    access_rules: Mapped[List["ColumnAccess"]] = relationship("ColumnAccess", back_populates="column", cascade="all, delete-orphan")
