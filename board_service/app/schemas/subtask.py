from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

class SubtaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    is_completed: bool = False
    position: int = Field(0, ge=0)
    settings: dict = Field(default_factory=dict)
    ai_metadata: dict = Field(default_factory=dict)

class SubtaskCreate(SubtaskBase):
    task_id: UUID

class SubtaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    is_completed: Optional[bool] = None
    position: Optional[int] = Field(None, ge=0)
    task_id: Optional[UUID] = None  # Supports re-parenting (drag-and-drop to another task)
    settings: Optional[dict] = None
    ai_metadata: Optional[dict] = None

class Subtask(SubtaskBase):
    id: UUID
    task_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)