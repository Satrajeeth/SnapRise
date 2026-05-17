import uuid 
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import AccessType, BoardRole


class ColumnAccess(Base):
    __tablename__ = "column_access"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    column_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("columns.id"), index=True)
    
    # Can restrict by specific user or by role
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    role_restriction: Mapped[Optional[BoardRole]] = mapped_column(Enum(BoardRole), nullable=True)
    
   

    access_type: Mapped[AccessType] = mapped_column(Enum(AccessType), default=AccessType.READ)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    #func.now() - When a new row is inserted, let the DATABASE automatically set the current timestamp.

    # Relationships
    column: Mapped["Column"] = relationship("Column", back_populates="access_rules")
    #back_populates links two ORM relationships together so SQLAlchemy knows they are opposite sides of the same relationship.
