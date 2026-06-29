from typing import List, Optional
from uuid import UUID 
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db_session
from app.schemas.board import (
    Board, BoardCreate, BoardUpdate,
    BoardMemberResponse, BoardMemberCreate, BoardMemberUpdate
)
from app.schemas.column import Column, ColumnCreate, ColumnUpdate
from app.schemas.task import Task, TaskCreate, TaskUpdate
from app.schemas.subtask import Subtask, SubtaskCreate, SubtaskUpdate
from app.schemas.task_link import TaskLink, TaskLinkCreate
from app.schemas.responses import BoardDetailed, TaskDetailed
from app.schemas.board_template import BoardTemplate as BoardTemplateSchema, BoardTemplateCreate, BoardTemplateUpdate
from app.schemas.invitation import InvitationCreate, InvitationResponse, AcceptInvitationResponse
from app.models.subtask import Subtask as SubtaskModel
from app.services.board_ops import BoardOps
from app.services.invitation_ops import InvitationOps
from app.services.ai_service import get_ai_service
from app.services.security_manager import get_security_manager
from app.services.metrics_service import MetricsService
from app.api.v1.dependencies import (
    get_current_user_id,
    require_viewer,
    require_owner,
    require_editor,
    get_board_id_from_column,
    get_board_id_from_task,
    get_board_id_from_subtask,
    check_column_access
)
from app.domain.enums import AccessType

security_manager = get_security_manager()
ai_service = get_ai_service()

router = APIRouter()

# Boards
@router.get("/boards", response_model=List[Board])
async def get_boards(db: AsyncSession = Depends(get_db_session), user_id: UUID = Depends(get_current_user_id)):
    return await BoardOps.get_boards(db, user_id = user_id)

@router.get("/boards/{board_id}", response_model=BoardDetailed)
async def get_board(board_id: UUID, db: AsyncSession = Depends(get_db_session), _role = Depends(require_viewer)):
    board = await BoardOps.get_board(db, board_id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    return board

@router.post("/boards", response_model=Board, status_code=status.HTTP_201_CREATED)
async def create_board(board_in: BoardCreate, db: AsyncSession = Depends(get_db_session),user_id: UUID = Depends(get_current_user_id)):
    return await BoardOps.create_board(db, board_in, owner_id=user_id)

@router.patch("/boards/{board_id}", response_model=Board)
async def update_board(board_id: UUID, board_in: BoardUpdate, db: AsyncSession = Depends(get_db_session), _role = Depends(require_editor)):
    board = await BoardOps.update_board(db, board_id, board_in)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    return board

@router.delete("/boards/{board_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_board(board_id: UUID, db: AsyncSession = Depends(get_db_session), _role = Depends(require_owner)):
    if not await BoardOps.delete_board(db, board_id):
        raise HTTPException(status_code=404, detail="Board not found")

# Board Members

@router.get("/boards/{board_id}/members", response_model=List[BoardMemberResponse])
async def get_board_members(
    board_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id)
):
    await require_viewer(board_id, user_id, db)
    return await BoardOps.get_board_members(db, board_id)

@router.post("/boards/{board_id}/members", response_model=BoardMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_board_member(
    board_id: UUID,
    member_in: BoardMemberCreate,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id)
):
    await require_owner(board_id, user_id, db)
    return await BoardOps.add_board_member(db, board_id, member_in.user_id, member_in.role)

@router.put("/boards/{board_id}/members/{target_user_id}", response_model=BoardMemberResponse)
async def update_board_member(
    board_id: UUID,
    target_user_id: UUID,
    member_in: BoardMemberUpdate,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id)
):
    await require_owner(board_id, user_id, db)
    member = await BoardOps.update_board_member(db, board_id, target_user_id, member_in.role)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return member

@router.delete("/boards/{board_id}/members/{target_user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_board_member(
    board_id: UUID,
    target_user_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id)
):
    await require_owner(board_id, user_id, db)
    if not await BoardOps.remove_board_member(db, board_id, target_user_id):
        raise HTTPException(status_code=404, detail="Member not found")

# Board Invitations
#
# Email-based invites split across two paths the FRONTEND orchestrates:
#   1. it asks auth /resolve-email — if the email is a known user it calls the
#      existing POST /members directly (no invitation needed);
#   2. if auth returns 404 it calls POST /invitations below, which records a
#      pending invitation + a marketing lead and logs the accept link.
# So this endpoint is only ever hit for emails with no account yet.

@router.post(
    "/boards/{board_id}/invitations",
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_board_invitation(
    board_id: UUID,
    invitation_in: InvitationCreate,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    await require_owner(board_id, user_id, db)
    return await InvitationOps.create_invitation(
        db, board_id, invitation_in.email, invitation_in.role, invited_by=user_id
    )


@router.get("/boards/{board_id}/invitations", response_model=List[InvitationResponse])
async def list_board_invitations(
    board_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    # Read-level: anyone who can view the board can see who's been invited.
    await require_viewer(board_id, user_id, db)
    return await InvitationOps.list_invitations(db, board_id)


@router.delete(
    "/boards/{board_id}/invitations/{invitation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_board_invitation(
    board_id: UUID,
    invitation_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    await require_owner(board_id, user_id, db)
    if not await InvitationOps.revoke_invitation(db, board_id, invitation_id):
        raise HTTPException(status_code=404, detail="Pending invitation not found")


@router.post("/boards/invitations/{token}/accept", response_model=AcceptInvitationResponse)
async def accept_board_invitation(
    token: str,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    # NOT board-gated: the caller isn't a member yet — possession of the token
    # plus a valid login is the authorization. The accepting user comes from the
    # JWT, so a link can only ever add its bearer.
    invitation = await InvitationOps.accept_invitation(db, token, user_id)
    return AcceptInvitationResponse(board_id=invitation.board_id, role=invitation.role)

#Columns

@router.post("/columns", response_model=Column, status_code=status.HTTP_201_CREATED)
async def create_column(column_in: ColumnCreate, db: AsyncSession = Depends(get_db_session), user_id: UUID = Depends(get_current_user_id)):
    # Check perimissions on the board
    await require_editor(column_in.board_id, user_id, db)
    return await BoardOps.create_column(db, column_in)

@router.patch("/columns/{column_id}", response_model=Column)
async def update_column(column_id: UUID, column_in: ColumnUpdate, db: AsyncSession =Depends(get_db_session), user_id: UUID = Depends(get_current_user_id)):
    board_id = await get_board_id_from_column(column_id, db)
    await require_editor(board_id, user_id, db)
    if not await check_column_access(column_id, user_id, db, AccessType.WRITE):
        raise HTTPException(status_code=403, detail="Column write access denied")
    column = await BoardOps.update_column(db, column_id, column_in)
    if not column:
        raise HTTPException(status_code=404, detail="Column not found")
    return column

@router.delete("/columns/{column_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_column(column_id: UUID, db: AsyncSession = Depends(get_db_session),user_id: UUID = Depends(get_current_user_id)):
    board_id = await get_board_id_from_column(column_id, db)
    await require_editor(board_id, user_id, db)
    if not await check_column_access(column_id, user_id, db, AccessType.WRITE):
        raise HTTPException(status_code=403, detail="Column write access denied")
    if not await BoardOps.delete_column(db, column_id):
        raise HTTPException(status_code=404, detail="Column not found")

#Tasks

@router.post("/tasks", response_model=Task, status_code=status.HTTP_201_CREATED)
async def create_task(task_in: TaskCreate, db: AsyncSession = Depends(get_db_session), user_id: UUID = Depends(get_current_user_id)):
    # A task being created has no id yet — resolve the board from its column.
    board_id = await get_board_id_from_column(task_in.column_id, db)
    await require_editor(board_id, user_id, db)
    if not await check_column_access(task_in.column_id, user_id, db, AccessType.WRITE):
        raise HTTPException(status_code=403, detail="Column write access denied")
    return await BoardOps.create_task(db, task_in)

@router.patch("/tasks/{task_id}", response_model=Task)
async def update_task(task_id: UUID, task_in: TaskUpdate, db: AsyncSession = Depends(get_db_session), user_id: UUID = Depends(get_current_user_id)):
    board_id = await get_board_id_from_task(task_id, db)
    await require_editor(board_id, user_id, db)
    
    # We must check column access for the existing task's column
    task = await BoardOps.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not await check_column_access(task.column_id, user_id, db, AccessType.WRITE):
        raise HTTPException(status_code=403, detail="Column write access denied")
    
    if task_in.column_id is not None and task_in.column_id != task.column_id:
        if not await check_column_access(task_in.column_id, user_id, db, AccessType.WRITE):
            raise HTTPException(status_code=403, detail="Destination column write access denied")
    task = await BoardOps.update_task(db, task_id, task_in)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: UUID, db: AsyncSession = Depends(get_db_session), user_id: UUID = Depends(get_current_user_id)):
    board_id = await get_board_id_from_task(task_id, db)
    await require_editor(board_id, user_id, db)
    
    task = await BoardOps.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not await check_column_access(task.column_id, user_id, db, AccessType.WRITE):
        raise HTTPException(status_code=403, detail="Column write access denied")
    if not await BoardOps.delete_task(db, task_id):
        raise HTTPException(status_code=404, detail="Task not found")

#Subtasks

@router.post("/subtasks", response_model=Subtask, status_code=status.HTTP_201_CREATED)
async def create_subtask(subtask_in: SubtaskCreate, db: AsyncSession = Depends(get_db_session), user_id: UUID = Depends(get_current_user_id)):
    # A subtask being created has no id yet — resolve the board from its parent task.
    board_id = await get_board_id_from_task(subtask_in.task_id, db)
    await require_editor(board_id, user_id, db)
    task = await BoardOps.get_task(db, subtask_in.task_id)
    if task and not await check_column_access(task.column_id, user_id, db, AccessType.WRITE):
        raise HTTPException(status_code=403, detail="Column write access denied")
    return await BoardOps.create_subtask(db, subtask_in)

@router.patch("/subtasks/{subtask_id}", response_model=Subtask)
async def update_subtask(subtask_id: UUID, subtask_in: SubtaskUpdate, db: AsyncSession = Depends(get_db_session), user_id: UUID = Depends(get_current_user_id)):
    board_id = await get_board_id_from_subtask(subtask_id, db)
    await require_editor(board_id, user_id, db)
    
    subtask_model = await db.get(SubtaskModel, subtask_id)
    if subtask_model:
        task = await BoardOps.get_task(db, subtask_model.task_id)
        if task and not await check_column_access(task.column_id, user_id, db, AccessType.WRITE):
            raise HTTPException(status_code=403, detail="Column write access denied")
            
        if subtask_in.task_id is not None and subtask_in.task_id != subtask_model.task_id:
            new_task = await BoardOps.get_task(db, subtask_in.task_id)
            if new_task and not await check_column_access(new_task.column_id, user_id, db, AccessType.WRITE):
                raise HTTPException(status_code=403, detail="Destination column write access denied")
                
    subtask = await BoardOps.update_subtask(db, subtask_id, subtask_in)
    if not subtask:
        raise HTTPException(status_code=404, detail="Subtask not found")
    return subtask

@router.delete("/subtasks/{subtask_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subtask(subtask_id: UUID, db: AsyncSession = Depends(get_db_session), user_id: UUID = Depends(get_current_user_id)):
    board_id = await get_board_id_from_subtask(subtask_id, db)
    await require_editor(board_id, user_id, db)
    
    subtask_model = await db.get(SubtaskModel, subtask_id)
    if subtask_model:
        task = await BoardOps.get_task(db, subtask_model.task_id)
        if task and not await check_column_access(task.column_id, user_id, db, AccessType.WRITE):
            raise HTTPException(status_code=403, detail="Column write access denied")
            
    if not await BoardOps.delete_subtask(db, subtask_id):
        raise HTTPException(status_code=404, detail="Subtask not found")

@router.get("/tasks/{task_id}", response_model=TaskDetailed)
async def get_task(task_id: UUID, include_linked_tasks: bool = False, db: AsyncSession = Depends(get_db_session), user_id: UUID = Depends(get_current_user_id)):
    board_id = await get_board_id_from_task(task_id, db)
    await require_viewer(board_id, user_id, db)
    task = await BoardOps.get_task(db, task_id, include_linked_tasks=include_linked_tasks)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not await check_column_access(task.column_id, user_id, db, AccessType.READ):
        raise HTTPException(status_code=403, detail="Column read access denied")
    return task

#AI Operations

@router.post("/tasks/{task_id}/ai-analyze")
async def analyze_task_ai(task_id: UUID, db: AsyncSession = Depends(get_db_session), user_id: UUID = Depends(get_current_user_id)):
    board_id = await get_board_id_from_task(task_id, db)
    await require_viewer(board_id, user_id, db)

    # 1. Fetch task with full context (including parents for AI permission check)
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.models.task import Task as TaskModel
    from app.models.column import Column as ColumnModel
    from app.models.board import Board as BoardModel

    result = await db.execute(
        select(TaskModel)
        .where(TaskModel.id == task_id)
        .options(
            selectinload(TaskModel.column).selectinload(ColumnModel.board),#selectinload() to load parent column and board for permission checks
            selectinload(TaskModel.subtasks)
        )
    )

    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    #2. Check AI permissions 
    if not security_manager.can_ai_process(task):
        raise HTTPException(status_code=403, detail="AI processing not allowed for this task")
    
    #3. Decrypt fields for AI if necessary 
    security_manager.process_task_after_load(task, task.column.board.encryption_status)

    # 4. Run AI analysis
    subtask_titles = [s.title for s in task.subtasks]
    
    summary = await ai_service.summarize_task(task.title, task.content)
    blockers = await ai_service.detect_blockers(task.title, task.content, subtask_titles)

    #5 . Update ai_metadata
    if not task.ai_metadata:
        task.ai_metadata = {}

    task.ai_metadata["auto_summary"] = summary
    task.ai_metadata["detected_blockers"] = blockers
    task.ai_metadata["last_ai_analysis"] = datetime.now().isoformat()

    await db.flush()

    return {
        "task_id": str(task_id),
        "summary": summary,
        "blockers": blockers
    }

@router.post("/tasks/{task_id}/ai-classify")
async def classify_task_ai(task_id: UUID, db: AsyncSession = Depends(get_db_session),user_id: UUID = Depends(get_current_user_id)):
    board_id = await get_board_id_from_task(task_id, db)
    await require_viewer(board_id, user_id, db)

    #1. Fetch task with board context 
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.models.task import Task as TaskModel
    from app.models.column import Column as ColumnModel
    from app.models.board import Board as BoardModel

    result = await db.execute(
        select(TaskModel)
        .where(TaskModel.id == task_id)
        .options(
            selectinload(TaskModel.column).selectinload(ColumnModel.board).selectinload(BoardModel.columns)
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    #2. Check AI permissions
    if not security_manager.can_ai_process(task):
        raise HTTPException(status_code=403, detail="AI processing not allowed for this task")
    
    #3. Decrypt fields for AI if necessary
    security_manager.process_task_after_load(task, task.column.board.encryption_status)

    #4. Run AI classification
    column_names = [c.name for c in task.column.board.columns]
    suggested_column = await ai_service.suggest_task_classification(task.title, task.content, column_names)

    return {
        "task_id": str(task_id),
        "suggested_column": suggested_column,
        "available_columns": column_names
    }

# Task Links

@router.post("/tasks/{task_id}/links", response_model=TaskLink, status_code=status.HTTP_201_CREATED)
async def create_task_link(
    task_id: UUID,
    link_in: TaskLinkCreate,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id)
):
    # Check permissions for source task
    source_board_id = await get_board_id_from_task(task_id, db)
    await require_editor(source_board_id, user_id, db)
    
    # Check permissions for target task (must be at least viewer)
    target_board_id = await get_board_id_from_task(link_in.target_task_id, db)
    await require_viewer(target_board_id, user_id, db)
    
    return await BoardOps.create_task_link(db, task_id, link_in)

@router.delete("/tasks/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task_link(
    link_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id)
):
    from app.models.task_link import TaskLink as TaskLinkModel
    link = await db.get(TaskLinkModel, link_id)
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
        
    # Check permissions for source task (must be editor to delete link)
    board_id = await get_board_id_from_task(link.source_task_id, db)
    await require_editor(board_id, user_id, db)
    
    if not await BoardOps.delete_task_link(db, link_id):
        raise HTTPException(status_code=404, detail="Link not found")


# Templates

@router.get("/templates", response_model=List[BoardTemplateSchema])
async def get_templates(
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id)
):
    return await BoardOps.get_templates(db, user_id=user_id)

@router.get("/templates/{template_id}", response_model=BoardTemplateSchema)
async def get_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id)
):
    template = await BoardOps.get_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    # Check access: must be owner or template must be public
    if template.owner_user_id != user_id and not template.is_public:
        raise HTTPException(status_code=403, detail="Access denied")
    return template

@router.post("/templates", response_model=BoardTemplateSchema, status_code=status.HTTP_201_CREATED)
async def create_template(
    template_in: BoardTemplateCreate,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id)
):
    return await BoardOps.create_template(db, template_in, owner_id=user_id)

@router.patch("/templates/{template_id}", response_model=BoardTemplateSchema)
async def update_template(
    template_id: UUID,
    template_in: BoardTemplateUpdate,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id)
):
    # Only owner can update
    existing = await BoardOps.get_template(db, template_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Template not found")
    if existing.owner_user_id != user_id:
        raise HTTPException(status_code=403, detail="Only the template owner can update it")
    template = await BoardOps.update_template(db, template_id, template_in)
    return template

@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id)
):
    existing = await BoardOps.get_template(db, template_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Template not found")
    if existing.owner_user_id != user_id:
        raise HTTPException(status_code=403, detail="Only the template owner can delete it")
    await BoardOps.delete_template(db, template_id)

@router.post("/boards/from-template", response_model=Board, status_code=status.HTTP_201_CREATED)
async def create_board_from_template(
    template_id: UUID,
    board_name: str,
    description: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id)
):
    """Create a new board from a template."""
    # Verify template exists and user has access
    template = await BoardOps.get_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if template.owner_user_id != user_id and not template.is_public:
        raise HTTPException(status_code=403, detail="Access denied")
    return await BoardOps.create_board_from_template(
        db, template_id, board_name, owner_id=user_id, description=description
    )

# Smart Features

@router.post("/boards/{board_id}/smart-sort", status_code=status.HTTP_200_OK)
async def board_smart_sort(
    board_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id)
):
    """Analyze all tasks and suggest re-ordering or flag blockers."""
    await require_editor(board_id, user_id, db)
    board = await BoardOps.get_board(db, board_id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
        
    tasks_content = []
    for col in getattr(board, "columns", []):
        for t in getattr(col, "tasks", []):
            tasks_content.append({"id": str(t.id), "title": t.title, "column": col.name})
    
    prompt = f"Analyze these tasks and suggest improvements, re-ordering, or identify bottlenecks:\n{tasks_content}"
    messages = [{"role": "system", "content": "You are a Kanban expert."}, {"role": "user", "content": prompt}]
    result = await ai_service.chat_completion(messages, max_tokens=300)
    return {"suggestions": result}

@router.post("/tasks/{task_id}/suggest-column")
async def suggest_task_column(
    task_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id)
):
    """Ask the AI to suggest which column this task belongs in based on content."""
    board_id = await get_board_id_from_task(task_id, db)
    await require_viewer(board_id, user_id, db)
    
    task = await BoardOps.get_task(db, task_id)
    if not task:
         raise HTTPException(status_code=404, detail="Task not found")
         
    # Need to fetch board details to get column names
    board = await BoardOps.get_board(db, board_id)
    col_names = [c.name for c in getattr(board, "columns", [])] if board else []
    
    suggestion = await ai_service.suggest_task_classification(task.title, task.content, col_names)
    return {"suggested_column": suggestion}

@router.get("/boards/{board_id}/metrics")
async def get_board_metrics(
    board_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id)
):
    await require_viewer(board_id, user_id, db)
    metrics = await MetricsService.get_board_metrics(db, board_id)
    if not metrics:
        raise HTTPException(status_code=404, detail="Board not found")
    return metrics
