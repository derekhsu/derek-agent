"""SQLite storage implementation for Derek Agent Runner."""

from pathlib import Path

from ..core.config import StorageConfig
from .sqlalchemy_storage import SQLAlchemyStorage


class SQLiteStorage(SQLAlchemyStorage):
    """Backward-compatible SQLite storage backed by SQLAlchemy."""

    def __init__(self, db_path: str | Path):
        """Initialize SQLite storage.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = Path(db_path)
        super().__init__(StorageConfig(type="sqlite", path=str(self.db_path)))
