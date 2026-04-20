"""Storage module for Derek Agent Runner."""

from ..core.config import StorageConfig
from .base import BaseStorage, Message, Session, UsageMetrics
from .sqlalchemy_storage import SQLAlchemyStorage
from .sqlite import SQLiteStorage


def create_storage(config: StorageConfig | None) -> BaseStorage:
    storage_config = config or StorageConfig()
    if storage_config.type == "sqlite":
        if storage_config.path:
            return SQLiteStorage(storage_config.path)
        return SQLAlchemyStorage(storage_config)
    return SQLAlchemyStorage(storage_config)


__all__ = [
    "BaseStorage",
    "Message",
    "Session",
    "SQLiteStorage",
    "SQLAlchemyStorage",
    "UsageMetrics",
    "create_storage",
]
