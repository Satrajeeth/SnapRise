import csv
import io
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import current_superuser, require_ingest_secret
from app.db.base import get_db_session
from app.domain.enums import LeadSource, LeadStatus
from app.schemas.lead import (
    LeadCreate,
    LeadIngestRequest,
    LeadIngestResponse,
    LeadListResponse,
    LeadResponse,
    LeadUpdate,
)
from app.services.lead_ops import LeadOps

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Superuser-facing lead management
# ---------------------------------------------------------------------------
@router.get("/leads", response_model=LeadListResponse)
async def list_leads(
    status_filter: Optional[LeadStatus] = Query(default=None, alias="status"),
    source: Optional[LeadSource] = Query(default=None),
    q: Optional[str] = Query(default=None, description="Search email/notes"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session),
    _admin: UUID = Depends(current_superuser),
) -> LeadListResponse:
    items, total = await LeadOps.list_leads(db, status_filter, source, q, limit, offset)
    return LeadListResponse(
        items=[LeadResponse.model_validate(lead) for lead in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/leads", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(
    lead_in: LeadCreate,
    db: AsyncSession = Depends(get_db_session),
    _admin: UUID = Depends(current_superuser),
) -> LeadResponse:
    lead = await LeadOps.create_lead(db, lead_in)
    return LeadResponse.model_validate(lead)


@router.get("/leads/export")
async def export_leads(
    status_filter: Optional[LeadStatus] = Query(default=None, alias="status"),
    source: Optional[LeadSource] = Query(default=None),
    q: Optional[str] = Query(default=None),
    format: str = Query(default="csv"),
    db: AsyncSession = Depends(get_db_session),
    _admin: UUID = Depends(current_superuser),
) -> StreamingResponse:
    """Export the (filtered) leads as CSV. Defined before /leads/{lead_id} so the
    literal "export" segment is matched here rather than as a UUID path param."""
    if format != "csv":
        raise HTTPException(status_code=400, detail="Only format=csv is supported")

    leads = await LeadOps.iter_export(db, status_filter, source, q)

    def generate():
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            ["id", "email", "source", "status", "board_id", "invited_by", "notes", "created_at", "updated_at"]
        )
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)
        for lead in leads:
            writer.writerow(
                [
                    str(lead.id),
                    lead.email,
                    lead.source.value,
                    lead.status.value,
                    str(lead.board_id) if lead.board_id else "",
                    str(lead.invited_by) if lead.invited_by else "",
                    lead.notes or "",
                    lead.created_at.isoformat() if lead.created_at else "",
                    lead.updated_at.isoformat() if lead.updated_at else "",
                ]
            )
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads.csv"},
    )


@router.get("/leads/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    _admin: UUID = Depends(current_superuser),
) -> LeadResponse:
    lead = await LeadOps.get_lead(db, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return LeadResponse.model_validate(lead)


@router.patch("/leads/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: UUID,
    patch: LeadUpdate,
    db: AsyncSession = Depends(get_db_session),
    _admin: UUID = Depends(current_superuser),
) -> LeadResponse:
    lead = await LeadOps.get_lead(db, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    lead = await LeadOps.update_lead(db, lead, patch)
    return LeadResponse.model_validate(lead)


# ---------------------------------------------------------------------------
# Internal ingest (board_service outbox drainer)
# ---------------------------------------------------------------------------
@router.post(
    "/internal/leads/ingest",
    response_model=LeadIngestResponse,
    dependencies=[Depends(require_ingest_secret)],
)
async def ingest_leads(
    body: LeadIngestRequest,
    db: AsyncSession = Depends(get_db_session),
) -> LeadIngestResponse:
    """Upsert a batch of leads forwarded from board_service's lead_outbox.

    Idempotent: replaying the same outbox rows produces no duplicates (unique on
    email+source+board_id) and never downgrades a converted lead.
    """
    created = updated = converted = 0
    for item in body.leads:
        was_created, was_converted = await LeadOps.upsert_lead(db, item)
        if was_created:
            created += 1
        else:
            updated += 1
        if was_converted:
            converted += 1

    return LeadIngestResponse(
        received=len(body.leads), created=created, updated=updated, converted=converted
    )
