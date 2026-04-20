"""Tests for SQLAlchemy storage migration and legacy SQLite upgrade."""

import sqlite3

import pytest

from src.core.config import StorageConfig
from src.storage import BaseStorage, Message, Session, SQLAlchemyStorage, SQLiteStorage, create_storage


@pytest.mark.asyncio
async def test_create_storage_returns_sqlalchemy_backed_sqlite_storage(tmp_path):
    db_path = tmp_path / "app.db"

    storage = create_storage(StorageConfig(type="sqlite", path=str(db_path)))

    assert isinstance(storage, BaseStorage)
    assert isinstance(storage, SQLAlchemyStorage)
    assert isinstance(storage, SQLiteStorage)


@pytest.mark.asyncio
async def test_initialize_upgrades_legacy_sqlite_database_and_preserves_data(tmp_path):
    db_path = tmp_path / "legacy.db"

    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE sessions (
            id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            title TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            metadata TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            metadata TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        "INSERT INTO sessions (id, agent_id, title, created_at, updated_at, metadata) VALUES (?, ?, ?, ?, ?, ?)",
        ("session-1", "agent-1", "Legacy", "2026-01-01T00:00:00", "2026-01-01T00:00:00", "{}"),
    )
    conn.execute(
        "INSERT INTO messages (session_id, role, content, timestamp, metadata) VALUES (?, ?, ?, ?, ?)",
        ("session-1", "user", "hello", "2026-01-01T00:00:01", "{}"),
    )
    conn.commit()
    conn.close()

    storage = create_storage(StorageConfig(type="sqlite", path=str(db_path)))
    await storage.initialize()

    session = await storage.get_session("session-1")
    assert session is not None
    assert session.title == "Legacy"
    assert len(session.messages) == 1
    assert session.messages[0].content == "hello"
    assert session.messages[0].metrics is None

    check = sqlite3.connect(db_path)
    columns = {row[1] for row in check.execute("PRAGMA table_info(messages)").fetchall()}
    tables = {row[0] for row in check.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    check.close()

    assert "metrics" in columns
    assert "alembic_version" in tables
