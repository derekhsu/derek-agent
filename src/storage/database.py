from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from ..core.config import StorageConfig


def resolve_storage_url(config: StorageConfig) -> str:
    if config.url:
        return config.url

    if config.type == "sqlite":
        db_path = Path(config.path or "derek-agent.db").expanduser().resolve()
        return f"sqlite:///{db_path}"

    raise ValueError(f"Unsupported storage type: {config.type}")


def create_engine_and_sessionmaker(
    database_url: str,
) -> tuple[Engine, sessionmaker[Session]]:
    engine = create_engine(database_url)
    session_factory = sessionmaker(engine, expire_on_commit=False)
    return engine, session_factory
