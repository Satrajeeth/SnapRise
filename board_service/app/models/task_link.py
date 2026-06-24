import uuid 
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import LinkType

class TaskLink(Base):
    __tablename__ = "task_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), index=True)
    target_task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), index=True)
    link_type: Mapped[LinkType] = mapped_column(
        Enum(LinkType, values_callable=lambda e: [m.value for m in e]), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    source_task: Mapped["Task"] = relationship(
        "Task", foreign_keys=[source_task_id], back_populates="source_links"
    )
    target_task: Mapped["Task"] = relationship(
        "Task", foreign_keys=[target_task_id], back_populates="target_links"
    )
