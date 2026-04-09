from sqlalchemy.ext.asyncio.session import AsyncSession


from sqlalchemy.orm.session import Session


from collections.abc import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

async_engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session_factory = async_sessionmaker[AsyncSession](async_engine, expire_on_commit=False)

sync_engine = create_engine(settings.SYNC_DATABASE_URL, echo=False)
sync_session_factory = sessionmaker[Session](sync_engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


def get_sync_db() -> Session:
    return sync_session_factory()
