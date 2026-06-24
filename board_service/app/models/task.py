import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import EncryptionStatus


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    column_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("columns.id"), index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0)

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
    column: Mapped["Column"] = relationship("Column", back_populates="tasks")
    subtasks: Mapped[List["Subtask"]] = relationship("Subtask", back_populates="task", cascade="all, delete-orphan")
    source_links: Mapped[List["TaskLink"]] = relationship(
		"TaskLink", foreign_keys="TaskLink.source_task_id", back_populates="source_task", cascade="all, delete-orphan"
	)
    target_links: Mapped[List["TaskLink"]] = relationship(
		"TaskLink", foreign_keys="TaskLink.target_task_id", back_populates="target_task", cascade="all, delete-orphan"
	)
