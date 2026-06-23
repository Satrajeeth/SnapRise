import sys
import os
from pathlib import Path

# Add board_service to sys.path to allow imports from app.*
# Current file: board_service/simulators/phase1/backend.py
# Root should be: SnapRise/board_service

# Line 12 what is does is __file__ - it take the path of the current file 
#   .resolve() - converts it into an absoulte path 
#   .parent - takes the parent directory of the current file (backend.py) and iterations of it goes back 3 dirctories
board_service_path = Path(__file__).resolve().parent.parent.parent
# sys.path is a list of directories that Python searches when you do an import.

# import sys
# print(sys.path)
# Output : [
#     '/home/jap/project/services/board/api',
#     '/usr/lib/python3.12',
#     '/usr/local/lib/python3.12/site-packages',
#     ...
# ]
sys.path.append(str(board_service_path))

# Mock settings before importing models
#This sets a environment variable 
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

# Patch PostgreSQL specific types for SQLite compatibility in the simulator
import sqlalchemy.dialects.postgresql
from sqlalchemy.types import JSON, String, TypeDecorator, CHAR
import uuid

class SQLiteUUID(TypeDecorator):
    impl = CHAR(36)
    cache_ok = True

    def __init__(self, *args, **kwargs):
        kwargs.pop("as_uuid", None)
        super().__init__(*args, **kwargs)

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return uuid.UUID(value)

sqlalchemy.dialects.postgresql.JSONB = JSON
sqlalchemy.dialects.postgresql.UUID = SQLiteUUID

import sqlalchemy.ext.asyncio
original_create_async_engine = sqlalchemy.ext.asyncio.create_async_engine

def patched_create_async_engine(url, **kwargs):
    if url.startswith("sqlite"):
        kwargs.pop("pool_size", None)
        kwargs.pop("max_overflow", None)
    return original_create_async_engine(url, **kwargs)

sqlalchemy.ext.asyncio.create_async_engine = patched_create_async_engine

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from typing import List, Optional
import uuid

# Now import models and other components from the main app
from app.models.board import Board
from app.db.base import Base
from app.core.security import EncryptionService
from app.domain.enums import EncryptionStatus, LifecycleStage

app = FastAPI(title="Phase 1 Simulator Backend")

# Enable CORS for Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# SQLite in-memory engine for isolation
engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=True)
SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        # Create tables in the in-memory SQLite DB
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

class BoardCreate(BaseModel):
    name: str
    description: str
    encrypt: bool

class BoardResponse(BaseModel):
    id: str
    name: str
    raw_description: str
    decrypted_description: str
    encryption_status: str

@app.post("/simulate/boards", response_model=BoardResponse)
async def create_board(board_in: BoardCreate, db: AsyncSession = Depends(get_db)):
    encryption_service = EncryptionService()
    
    description = board_in.description
    status = EncryptionStatus.DISABLED
    
    if board_in.encrypt:
        # Using the actual encryption utility from the codebase
        description = encryption_service.encrypt(board_in.description)
        status = EncryptionStatus.ENABLED
    
    new_board = Board(
        name=board_in.name,
        description=description,
        encryption_status=status,
        lifecycle_stage=LifecycleStage.ACTIVE
    )
    
    db.add(new_board)
    await db.flush()
    
    decrypted = encryption_service.decrypt(new_board.description) if board_in.encrypt else new_board.description
    
    return BoardResponse(
        id=str(new_board.id),
        name=new_board.name,
        raw_description=new_board.description,
        decrypted_description=decrypted,
        encryption_status=new_board.encryption_status.value
    )

@app.get("/simulate/boards", response_model=List[BoardResponse])
async def list_boards(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Board))
    boards = result.scalars().all()
    
    encryption_service = EncryptionService()
    
    responses = []
    for b in boards:
        decrypted = encryption_service.decrypt(b.description) if b.encryption_status == EncryptionStatus.ENABLED else b.description
        responses.append(BoardResponse(
            id=str(b.id),
            name=b.name,
            raw_description=b.description,
            decrypted_description=decrypted,
            encryption_status=b.encryption_status.value
        ))
    return responses

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
