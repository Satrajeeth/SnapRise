from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from app.domain.enums import LinkType
from .task import TaskMinimal

class TaskLinkBase(BaseModel):
    target_task_id: UUID
    link_type: LinkType

class TaskLinkCreate(TaskLinkBase):
    pass

class TaskLink(TaskLinkBase):
    id: UUID
    source_task_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TaskLinkDetailed(TaskLink):
    target_task: Optional[TaskMinimal] = None
    source_task: Optional[TaskMinimal] = None
