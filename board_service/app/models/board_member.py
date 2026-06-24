import uuid 
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
#Mapped is a anotation helper . Used to make a schema field like this field belongs to the database model
#mapped_column is used to define the column in the database and its properties
#relationship is used to define the relationship between two tables in the database

from app.db.base import Base
from app.domain.enums import BoardRole


class BoardMember(Base):
    __tablename__ = "board_members"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    board_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("boards.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    # values_callable → store/read the lowercase enum *values* (owner/editor/viewer),
    # matching the existing Postgres `boardrole` type. Without it SQLAlchemy binds the
    # member NAME ("OWNER"), which the DB enum rejects.
    role: Mapped[BoardRole] = mapped_column(
        Enum(BoardRole, values_callable=lambda e: [m.value for m in e]),
        default=BoardRole.VIEWER,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    #Relationships
    board: Mapped["Board"] = relationship("Board", back_populates="members")
