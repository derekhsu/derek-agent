"""SQLite storage implementation for Derek Agent Runner."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

import aiosqlite

from .base import BaseStorage, Message, Session


class SQLiteStorage(BaseStorage):
    """SQLite-based storage implementation."""

    def __init__(self, db_path: str | Path):
        """Initialize SQLite storage.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = Path(db_path)
        self._db: aiosqlite.Connection | None = None

    async def _get_db(self) -> aiosqlite.Connection:
        """Get or create database connection."""
        if self._db is None:
            self._db = await aiosqlite.connect(self.db_path)
            self._db.row_factory = aiosqlite.Row
        return self._db

    async def initialize(self) -> None:
        """Create tables if they don't exist."""
        db = await self._get_db()

        # Create sessions table
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                title TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                metadata TEXT
            )
            """
        )

        # Create messages table
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
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

        # Create index on messages.session_id
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)"
        )

        await db.commit()

    async def create_session(self, session: Session) -> Session:
        """Create a new session."""
        db = await self._get_db()
        await db.execute(
            """
            INSERT INTO sessions (id, agent_id, title, created_at, updated_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                session.id,
                session.agent_id,
                session.title,
                session.created_at.isoformat(),
                session.updated_at.isoformat(),
                json.dumps(session.metadata),
            ),
        )
        await db.commit()
        return session

    async def get_session(self, session_id: str) -> Session | None:
        """Get a session by ID with all messages."""
        db = await self._get_db()

        # Get session
        cursor = await db.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        )
        row = await cursor.fetchone()

        if not row:
            return None

        # Get messages
        messages = await self.get_messages(session_id)

        return Session(
            id=row["id"],
            agent_id=row["agent_id"],
            title=row["title"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            messages=messages,
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )

    async def list_sessions(
        self, agent_id: str | None = None, limit: int = 50
    ) -> list[Session]:
        """List sessions, optionally filtered by agent."""
        db = await self._get_db()

        if agent_id:
            cursor = await db.execute(
                """
                SELECT * FROM sessions WHERE agent_id = ?
                ORDER BY updated_at DESC LIMIT ?
                """,
                (agent_id, limit),
            )
        else:
            cursor = await db.execute(
                """
                SELECT * FROM sessions
                ORDER BY updated_at DESC LIMIT ?
                """,
                (limit,),
            )

        rows = await cursor.fetchall()

        sessions = []
        for row in rows:
            sessions.append(
                Session(
                    id=row["id"],
                    agent_id=row["agent_id"],
                    title=row["title"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                    messages=[],  # Don't load messages for list view
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                )
            )

        return sessions

    async def update_session(self, session: Session) -> Session:
        """Update a session."""
        db = await self._get_db()
        session.updated_at = datetime.now()

        await db.execute(
            """
            UPDATE sessions
            SET title = ?, updated_at = ?, metadata = ?
            WHERE id = ?
            """,
            (
                session.title,
                session.updated_at.isoformat(),
                json.dumps(session.metadata),
                session.id,
            ),
        )
        await db.commit()
        return session

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and its messages."""
        db = await self._get_db()
        cursor = await db.execute(
            "DELETE FROM sessions WHERE id = ?", (session_id,)
        )
        await db.commit()
        return cursor.rowcount > 0

    async def add_message(self, session_id: str, message: Message) -> Message:
        """Add a message to a session."""
        db = await self._get_db()

        await db.execute(
            """
            INSERT INTO messages (session_id, role, content, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session_id,
                message.role,
                message.content,
                message.timestamp.isoformat(),
                json.dumps(message.metadata),
            ),
        )

        # Update session updated_at
        await db.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (datetime.now().isoformat(), session_id),
        )

        await db.commit()
        return message

    async def get_messages(self, session_id: str) -> list[Message]:
        """Get all messages in a session."""
        db = await self._get_db()

        cursor = await db.execute(
            """
            SELECT * FROM messages WHERE session_id = ?
            ORDER BY timestamp ASC
            """,
            (session_id,),
        )
        rows = await cursor.fetchall()

        return [
            Message(
                role=row["role"],
                content=row["content"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            )
            for row in rows
        ]

    async def close(self) -> None:
        """Close database connection."""
        if self._db:
            await self._db.close()
            self._db = None
