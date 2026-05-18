from typing import List
from uuid import UUID 
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db_session
from app.schemas.board import Board, BoardCreate, BoardUpdate
from app.schemas.column import Column, ColumnCreate, ColumnUpdate
from app.schemas.task import Task, TaskCreate, TaskUpdate
from app.schemas.subtask import Subtask, SubtaskCreate, SubtaskUpdate
from app.schemas.responses import BoardDetailed 
from app.services.board_ops import BoardOps
from app.services.ai_service import get_ai_service
from app.services.security_manager import get_security_manager
from app.api.v1.dependencies import(
    get_current_user_id,
    require_viewer,
    require_owner,
    require_editor,
    get_board_id_from_column,
    get_board_id_from_task,
    get_board_id_from_subtask
)

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
    column = await BoardOps.update_column(db, column_id, column_in)
    if not column:
        raise HTTPException(status_code=404, detail="Column not found")
    return column

@router.delete("/columns/{column_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_column(column_id: UUID, db: AsyncSession = Depends(get_db_session),user_id: UUID = Depends(get_current_user_id)):
    board_id = await get_board_id_from_column(column_id, db)
    await require_editor(board_id, user_id, db)
    if not await BoardOps.delete_column(db, column_id):
        raise HTTPException(status_code=404, detail="Column not found")

#Tasks

@router.post("/tasks", response_model=Task, status_code=status.HTTP_201_CREATED)
async def create_task(task_in: TaskCreate, db: AsyncSession = Depends(get_db_session), user_id: UUID = Depends(get_current_user_id)):
    board_id = await get_board_id_from_task(task_in.column_id, db)
    await require_editor(board_id, user_id, db)
    return await BoardOps.create_task(db, task_in)

@router.patch("/tasks/{task_id}", response_model=Task)
async def update_task(task_id: UUID, task_in: TaskUpdate, db: AsyncSession = Depends(get_db_session), user_id: UUID = Depends(get_current_user_id)):
    board_id = await get_board_id_from_task(task_id, db)
    await require_editor(board_id, user_id, db)
    task = await BoardOps.update_task(db, task_id, task_in)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: UUID, db: AsyncSession = Depends(get_db_session), user_id: UUID = Depends(get_current_user_id)):
    board_id = await get_board_id_from_task(task_id, db)
    await require_editor(board_id, user_id, db)
    if not await BoardOps.delete_task(db, task_id):
        raise HTTPException(status_code=404, detail="Task not found")

#Subtasks

@router.post("/subtasks", response_model=Subtask, status_code=status.HTTP_201_CREATED)
async def create_subtask(subtask_in: SubtaskCreate, db: AsyncSession = Depends(get_db_session), user_id: UUID = Depends(get_current_user_id)):
    board_id = await get_board_id_from_subtask(subtask_in.task_id, db)
    await require_editor(board_id, user_id, db)
    return await BoardOps.create_subtask(db, subtask_in)

@router.patch("/subtasks/{subtask_id}", response_model=Subtask)
async def update_subtask(subtask_id: UUID, subtask_in: SubtaskUpdate, db: AsyncSession = Depends(get_db_session), user_id: UUID = Depends(get_current_user_id)):
    board_id = await get_board_id_from_subtask(subtask_id, db)
    await require_editor(board_id, user_id, db)
    subtask = await BoardOps.update_subtask(db, subtask_id, subtask_in)
    if not subtask:
        raise HTTPException(status_code=404, detail="Subtask not found")
    return subtask

@router.delete("/subtasks/{subtask_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subtask(subtask_id: UUID, db: AsyncSession = Depends(get_db_session), user_id: UUID = Depends(get_current_user_id)):
    board_id = await get_board_id_from_subtask(subtask_id, db)
    await require_editor(board_id, user_id, db)
    if not await BoardOps.delete_subtask(db, subtask_id):
        raise HTTPException(status_code=404, detail="Subtask not found")



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

