from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from ..core.config import StorageConfig


def resolve_storage_url(config: StorageConfig) -> str:
    if config.url:
        return config.url

    if config.type == "sqlite":
        db_path = Path(config.path or "derek-agent.db").expanduser().resolve()
        return f"sqlite:///{db_path}"

    raise ValueError(f"Unsupported storage type: {config.type}")


def resolve_async_storage_url(config: StorageConfig) -> str:
    """Resolve storage URL for async database connection."""
    if config.url:
        # Convert sync URL to async if needed
        if config.url.startswith("sqlite:///"):
            return config.url.replace("sqlite:///", "sqlite+aiosqlite:///")
        elif config.url.startswith("postgresql://"):
            return config.url.replace("postgresql://", "postgresql+asyncpg://")
        elif config.url.startswith("mysql://"):
            return config.url.replace("mysql://", "mysql+aiomysql://")
        return config.url

    if config.type == "sqlite":
        db_path = Path(config.path or "derek-agent.db").expanduser().resolve()
        return f"sqlite+aiosqlite:///{db_path}"

    raise ValueError(f"Unsupported storage type: {config.type}")


def create_engine_and_sessionmaker(
    database_url: str,
) -> tuple[Engine, sessionmaker[Session]]:
    engine = create_engine(database_url)
    session_factory = sessionmaker(engine, expire_on_commit=False)
    return engine, session_factory


def create_async_engine_and_sessionmaker(
    database_url: str,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return engine, session_factory
