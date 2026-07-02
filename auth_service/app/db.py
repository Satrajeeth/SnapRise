from collections.abc import AsyncGenerator

from fastapi import Depends
from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTableUUID, SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Boolean

from app.config import get_settings

settings = get_settings()


class Base(DeclarativeBase):
    pass


class User(SQLAlchemyBaseUserTableUUID, Base):

    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    username: Mapped[str | None] = mapped_column(String(32), 
                                                 unique=True,
                                                 index=True,
                                                 nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512),
                                                   nullable=True)
    avatar_is_public: Mapped[bool] = mapped_column(Boolean,
                                                   default=False,
                                                   server_default="false",
                                                   nullable=False)


engine = create_async_engine(settings.database_url, pool_pre_ping=True)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def create_db_and_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)
