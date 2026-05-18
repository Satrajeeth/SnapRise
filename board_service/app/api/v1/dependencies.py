import jwt
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings 
from app.db.base import get_db_session
from app.domain.enums import BoardRole
from app.models.board_member import BoardMember
from app.models.column import Column
from app.models.task import Task
from app.models.subtask import Subtask

"""OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False) creates a FastAPI authentication 
dependency that extracts a Bearer token from the request header, uses auth/login as the login 
endpoint reference, and returns None instead of raising an error if the token is missing."""
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)

async def get_current_user_id(token: str = Depends(oauth2_scheme)) -> UUID:
    if not token:
        raise HTTPException(
            status_code= status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing sub claim",
            )
        return UUID(user_id)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

async def get_board_role(
        board_id: UUID,
        user_id: UUID = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db_session)
) -> Optional[BoardRole]:
    result = await db.execute(
        select(BoardMember.role).where(
            BoardMember.board_id == board_id,
            BoardMember.user_id == user_id
        )
        return result.scalar_one_or_none()
    )

class BoardPermisssionChecker:
    def __init__(self, required_role: list[BoardRole]):
        self.required_role = required_role

    #async def __call__(...) makes a Python object callable like a function and allows it to run asynchronously using await
    async def __call__(
            self,
            board_id: UUID,
            user_id: UUID = Depends(get_current_user_id),
            db: AsyncSession = Depends(get_db_session)
    ) -> BoardRole:
        role = await get_board_role(board_id, user_id, db)
        if not role or role not in self.required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return role

 # Specific role requirements
require_owner = BoardPermisssionChecker([BoardRole.OWNER])
require_editor = BoardPermisssionChecker([BoardRole.OWNER, BoardRole.EDITOR])
require_viewer = BoardPermisssionChecker([BoardRole.OWNER, BoardRole.EDITOR, BoardRole.VIEWER])

async def get_board_id_from_column(column_id: UUID, db: AsyncSession) -> UUID:
    result = await db.execute(select(Column.board_id).where(Column.id == column_id))
    board_id = result.scalar_one_or_none()
    if not board_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Column not found")
    return board_id

async def get_board_id_from_task(task_id: UUID, db: AsyncSession) -> UUID:
    result = await db.execute(
        select(Column.board_id)
        .join(Task, Column.id == Task.column_id)
        .where(Task.id == task_id)
    )
    board_id = result.scalar_one_or_none()
    if not board_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return board_id

async def get_board_id_from_task(task_id: UUID, db: AsyncSession) -> UUID:
    result = await db.execute(
        select(Column.board_id)
        .join(Task, Column.id == Task.column_id)
        .join(Subtask, Task.id == Subtask.task_id)
        .where(Task.id == task_id)
    )
    board_id = result.scalar_one_or_none()
    if not board_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subtask not found")
    return board_id