from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from sqlalchemy.orm import declarative_base
from app.config import get_settings 

#Base ORM Model

Base = declarative_base()

#Engine Configuration
# settings = get_settings()

# engine = create_async_engine(
#     settings.database_url,
#     echo=settings.debug or settings.database_echo,
#     pool_size=settings.database_pool_size,
#     max_overflow=settings.database_max_overflow,
#     future=True,
# )

_engine = None
_SessionLocal = None

def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.debug or settings.database_echo,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            future=True,
        )
    return _engine

engine=get_engine()

#Session Factory
SessionLocal = async_sessionmaker(
    bind=get_engine(),
    class_=AsyncSession,
    expire_on_commit=False,
)

#Database Dependency

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


