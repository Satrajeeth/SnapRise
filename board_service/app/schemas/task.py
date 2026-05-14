from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import EncryptionStatus

class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: Optional[str] = None
    position: int = Field(0, ge=0)
    encryption_status: EncryptionStatus = EncryptionStatus.DISABLED
    settings: dict = Field(default_factory=dict)
    ai_metadata: dict = Field(default_factory=dict)
    custom_fields: dict = Field(default_factory=dict)

class TaskCreate(TaskBase):
    column_id: UUID

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    content: Optional[str] = None
    position: Optional[int] = Field(None, ge=0)
    column_id: Optional[UUID] = None
    encryption_status: Optional[EncryptionStatus] = None
    settings: Optional[dict] = None
    ai_metadata: Optional[dict] = None
    custom_fields: Optional[dict] = None

class Task(TaskBase):
    id: UUID
    column_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
