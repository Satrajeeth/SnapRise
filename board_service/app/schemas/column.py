from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

class ColumnBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    position: int = Field(0, ge=0)
    wip_limit: Optional[int] = Field(None, ge=1)
    settings: dict = Field(default_factory=dict)
    ai_metadata: dict = Field(default_factory=dict)

class ColumnCreate(ColumnBase):
    board_id: UUID

class ColumnUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    position: Optional[int] = Field(None, ge=0) #ge means greater than or equal to
    wip_limit: Optional[int] = Field(None, ge=1)
    settings: Optional[dict] = None
    ai_metadata: Optional[dict] = None

class Column(ColumnBase):
    id: UUID
    board_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
