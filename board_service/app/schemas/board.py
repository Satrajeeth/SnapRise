from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import LifecycleStage, EncryptionStatus, BoardRole

class BoardMemberBase(BaseModel):
    user_id: UUID
    role: BoardRole = BoardRole.VIEWER

class BoardMemberCreate(BoardMemberBase):
    pass

class BoardMemberUpdate(BaseModel):
    role: BoardRole

class BoardMemberResponse(BoardMemberBase):
    id: UUID
    board_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class BoardBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1024)
    lifecycle_stage: LifecycleStage = LifecycleStage.ACTIVE
    encryption_status: EncryptionStatus = EncryptionStatus.DISABLED
    settings: dict = Field(default_factory=dict)
    ai_metadata: dict = Field(default_factory=dict)
    custom_fields: dict = Field(default_factory=dict)

class BoardCreate(BoardBase):
    pass

class BoardUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1024)
    lifecycle_stage: Optional[LifecycleStage] = None
    encryption_status: Optional[EncryptionStatus] = None
    settings: Optional[dict] = None
    ai_metadata: Optional[dict] = None
    custom_fields: Optional[dict] = None

class Board(BoardBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
