import jwt
from typing import Optional
from uuid import UUID

import hashlib
from fastapi import Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings 
from app.db.base import get_db_session
from app.domain.enums import AccessType, BoardRole
from app.models.board_member import BoardMember
from app.models.column import Column
from app.models.task import Task
from app.models.subtask import Subtask

"""OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False) creates a FastAPI authentication 
dependency that extracts a Bearer token from the request header, uses auth/login as the login 
endpoint reference, and returns None instead of raising an error if the token is missing."""
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_user_from_api_key(
    api_key: str = Security(api_key_header),
    db: AsyncSession = Depends(get_db_session)
) -> Optional[UUID]:
    if not api_key:
        return None
    
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    from app.models.api_key import ApiKey
    result = await db.execute(
        select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active == True)
    )
    key_record = result.scalar_one_or_none()
    if key_record:
        return key_record.user_id
    return None

async def get_current_user_id(
    db: AsyncSession = Depends(get_db_session),
    token: str = Depends(oauth2_scheme),
    api_key_user: Optional[UUID] = Depends(get_user_from_api_key)
) -> UUID:
    if api_key_user:
        return api_key_user
        
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return UUID(user_id_str)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

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
    )
    return result.scalar_one_or_none()

class BoardPermissionChecker:
    def __init__(self, required_roles: list[BoardRole]):
        self.required_roles = required_roles

    #async def __call__(...) makes a Python object callable like a function and allows it to run asynchronously using await
    async def __call__(
        self,
        board_id: UUID,
        user_id: UUID = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db_session),
    ) -> BoardRole:
        role = await get_board_role(board_id, user_id, db)
        if not role or role not in self.required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return role

 # Specific role requirements
require_owner = BoardPermissionChecker([BoardRole.OWNER])
require_editor = BoardPermissionChecker([BoardRole.OWNER, BoardRole.EDITOR])
require_viewer = BoardPermissionChecker([BoardRole.OWNER, BoardRole.EDITOR, BoardRole.VIEWER])

async def get_board_id_from_column(column_id: UUID, db: AsyncSession) -> UUID:
    result = await db.execute(select(Column.board_id).where(Column.id == column_id))
    board_id = result.scalar_one_or_none()
    if not board_id:
        raise HTTPException(status_code=404, detail="Column not found")
    return board_id

async def get_board_id_from_task(task_id: UUID, db: AsyncSession) -> UUID:
    result = await db.execute(
        select(Column.board_id)
        .join(Task, Column.id == Task.column_id)
        .where(Task.id == task_id)
    )
    board_id = result.scalar_one_or_none()
    if not board_id:
        raise HTTPException(status_code=404, detail="Task not found")
    return board_id

async def get_board_id_from_subtask(subtask_id: UUID, db: AsyncSession) -> UUID:
    result = await db.execute(
        select(Column.board_id)
        .join(Task, Column.id == Task.column_id)
        .join(Subtask, Task.id == Subtask.task_id)
        .where(Subtask.id == subtask_id)
    )
    board_id = result.scalar_one_or_none()
    if not board_id:
        raise HTTPException(status_code=404, detail="Subtask not found")
    return board_id


async def check_column_access(
    column_id: UUID,
    user_id: UUID,
    db: AsyncSession,
    required_access: "AccessType" = None,
) -> bool:
    """Check if user has column-level access. Returns True if access is allowed.
    
    Column access rules are additive restrictions — if no rules exist for a column,
    access is governed solely by board-level permissions. If rules exist, the user
    must match at least one rule.
    """
    from app.models.column_access import ColumnAccess
    from app.domain.enums import AccessType, BoardRole

    # Check if any access rules exist for this column
    rules_result = await db.execute(
        select(ColumnAccess).where(ColumnAccess.column_id == column_id)
    )
    rules = rules_result.scalars().all()

    # If no rules are defined, column inherits board-level permissions
    if not rules:
        return True

    # Get user's board role for role-based restriction matching
    board_id = await get_board_id_from_column(column_id, db)
    user_role = await get_board_role(board_id, user_id, db)

    for rule in rules:
        # Check access type if specified
        if required_access and rule.access_type != required_access:
            continue

        # Match by specific user
        if rule.user_id and rule.user_id == user_id:
            return True

        # Match by role restriction
        if rule.role_restriction and user_role == rule.role_restriction:
            return True

        # If rule has neither user_id nor role_restriction, it applies to everyone
        if not rule.user_id and not rule.role_restriction:
            return True

    return False
