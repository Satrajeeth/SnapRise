from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ColumnTemplatePayload(BaseModel):
    """Schema for a single column within a template payload."""
    name: str = Field(..., min_length=1, max_length=255)
    position: int = Field(0, ge=0)
    wip_limit: Optional[int] = Field(None, ge=1)
    settings: dict = Field(default_factory=dict)


class BoardTemplatePayload(BaseModel):
    """Schema for the full template payload containing columns and board settings."""
    columns: List[ColumnTemplatePayload] = []
    settings: dict = Field(default_factory=dict)
    custom_fields_schema: List[Dict[str, Any]] = []


class BoardTemplateBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1024)
    is_public: bool = False
    payload: BoardTemplatePayload = Field(default_factory=BoardTemplatePayload)


class BoardTemplateCreate(BoardTemplateBase):
    pass


class BoardTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1024)
    is_public: Optional[bool] = None
    payload: Optional[BoardTemplatePayload] = None


class BoardTemplate(BoardTemplateBase):
    id: UUID
    owner_user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
