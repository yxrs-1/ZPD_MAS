import os

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from zpd_api.models import Base


def database_url() -> str:
    return os.environ["DATABASE_URL"]


def sync_database_url() -> str:
    return database_url().replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)


def async_engine():
    return create_async_engine(database_url())


_sessions = None


def session_factory():
    global _sessions
    if _sessions is None:
        _sessions = async_sessionmaker(async_engine(), expire_on_commit=False)
    return _sessions


def sync_session_factory():
    engine = create_engine(sync_database_url())
    return sessionmaker(engine)


async def init_db() -> None:
    engine = async_engine()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await engine.dispose()
