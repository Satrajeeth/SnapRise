import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domain.enums import LeadSource, LeadStatus


# ---------------------------------------------------------------------------
# Human (superuser) facing
# ---------------------------------------------------------------------------
class LeadResponse(BaseModel):
    """Wire shape for a lead. `metadata` reads the ORM's `lead_metadata`
    attribute (the column is `metadata`, which can't be a mapped attribute name
    because it collides with SQLAlchemy's Base.metadata)."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    email: str
    source: LeadSource
    board_id: Optional[uuid.UUID] = None
    invited_by: Optional[uuid.UUID] = None
    status: LeadStatus
    notes: Optional[str] = None
    metadata: dict = Field(default_factory=dict, validation_alias="lead_metadata")
    created_at: datetime
    updated_at: datetime


class LeadListResponse(BaseModel):
    items: List[LeadResponse]
    total: int
    limit: int
    offset: int


class LeadCreate(BaseModel):
    """Manual lead entry from the backoffice (campaigns / promotions)."""

    email: EmailStr
    source: LeadSource = LeadSource.PROMOTION
    notes: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class LeadUpdate(BaseModel):
    """PATCH: only status and notes are editable by an admin."""

    status: Optional[LeadStatus] = None
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Internal ingest (board_service outbox drainer -> admin_service)
# ---------------------------------------------------------------------------
class LeadIngestItem(BaseModel):
    """One lead_outbox row as forwarded by board_service.

    `source` is the free-form outbox source ("board_invite" /
    "board_invite_accept"); admin_service normalizes it to a LeadSource and reads
    `payload.conversion` to decide whether this row marks a conversion.
    """

    email: EmailStr
    source: str = "board_invite"
    board_id: Optional[uuid.UUID] = None
    invited_by: Optional[uuid.UUID] = None
    payload: dict = Field(default_factory=dict)


class LeadIngestRequest(BaseModel):
    leads: List[LeadIngestItem] = Field(default_factory=list)


class LeadIngestResponse(BaseModel):
    received: int
    created: int
    updated: int
    converted: int
