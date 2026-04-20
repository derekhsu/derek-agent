from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..core.config import StorageConfig
from .base import BaseStorage, Message, Session, UsageMetrics
from .database import create_async_engine_and_sessionmaker, resolve_async_storage_url
from .models import MessageModel, SessionModel


class AsyncSQLAlchemyStorage(BaseStorage):
    """Async version of SQLAlchemy storage for better performance in async contexts."""

    def __init__(self, config: StorageConfig):
        self.config = config
        self.database_url = resolve_async_storage_url(config)
        self._engine, self._session_factory = create_async_engine_and_sessionmaker(self.database_url)

    async def initialize(self) -> None:
        """Initialize the database (run migrations)."""
        # For now, we'll use the existing sync migration system
        # In a full implementation, we'd have async migrations too
        from .migrations import upgrade_database
        
        # Convert async URL back to sync for migrations
        sync_url = self.database_url.replace("sqlite+aiosqlite:///", "sqlite:///")
        upgrade_database(sync_url)

    async def create_session(self, session: Session) -> Session:
        async with self._session_factory() as db:
            db.add(
                SessionModel(
                    id=session.id,
                    agent_id=session.agent_id,
                    title=session.title,
                    created_at=session.created_at.isoformat(),
                    updated_at=session.updated_at.isoformat(),
                    metadata_json=json.dumps(session.metadata),
                    is_compressed=session.is_compressed,
                )
            )
            await db.commit()
        return session

    async def get_session(self, session_id: str) -> Session | None:
        async with self._session_factory() as db:
            result = await db.execute(
                select(SessionModel)
                .options(selectinload(SessionModel.messages))
                .where(SessionModel.id == session_id)
            )
            row = result.scalar_one_or_none()
            if row is None:
                return None
            return self._to_session(row, include_messages=True)

    async def list_sessions(
        self, agent_id: str | None = None, limit: int = 50
    ) -> list[Session]:
        async with self._session_factory() as db:
            stmt = select(SessionModel).order_by(SessionModel.updated_at.desc()).limit(limit)
            if agent_id:
                stmt = stmt.where(SessionModel.agent_id == agent_id)
            result = await db.execute(stmt)
            rows = result.scalars().all()
            return [self._to_session(row, include_messages=False) for row in rows]

    async def update_session(self, session: Session) -> Session:
        session.updated_at = datetime.now()
        async with self._session_factory() as db:
            result = await db.execute(select(SessionModel).where(SessionModel.id == session.id))
            row = result.scalar_one_or_none()
            if row is None:
                raise ValueError(f"Session not found: {session.id}")
            row.title = session.title
            row.updated_at = session.updated_at.isoformat()
            row.metadata_json = json.dumps(session.metadata)
            row.is_compressed = session.is_compressed
            await db.commit()
        return session

    async def delete_session(self, session_id: str) -> bool:
        async with self._session_factory() as db:
            result = await db.execute(delete(SessionModel).where(SessionModel.id == session_id))
            await db.commit()
            return result.rowcount > 0

    async def add_message(self, session_id: str, message: Message) -> Message:
        async with self._session_factory() as db:
            db.add(
                MessageModel(
                    session_id=session_id,
                    role=message.role,
                    content=message.content,
                    timestamp=message.timestamp.isoformat(),
                    metadata_json=json.dumps(message.metadata),
                    metrics_json=json.dumps(message.metrics.to_dict()) if message.metrics else None,
                    message_type=message.message_type,
                )
            )
            result = await db.execute(select(SessionModel).where(SessionModel.id == session_id))
            session_row = result.scalar_one_or_none()
            if session_row is None:
                raise ValueError(f"Session not found: {session_id}")
            session_row.updated_at = datetime.now().isoformat()
            await db.commit()
        return message

    async def get_messages(self, session_id: str) -> list[Message]:
        async with self._session_factory() as db:
            result = await db.execute(
                select(MessageModel)
                .where(MessageModel.session_id == session_id)
                .order_by(MessageModel.timestamp.asc(), MessageModel.id.asc())
            )
            rows = result.scalars().all()
            return [self._to_message(row) for row in rows]

    async def close(self) -> None:
        await self._engine.dispose()

    def _to_session(self, row: SessionModel, include_messages: bool) -> Session:
        messages = [self._to_message(message) for message in row.messages] if include_messages else []
        return Session(
            id=row.id,
            agent_id=row.agent_id,
            title=row.title,
            created_at=datetime.fromisoformat(row.created_at),
            updated_at=datetime.fromisoformat(row.updated_at),
            messages=messages,
            metadata=json.loads(row.metadata_json) if row.metadata_json else {},
            is_compressed=row.is_compressed if row.is_compressed is not None else False,
        )

    def _to_message(self, row: MessageModel) -> Message:
        metrics = None
        if row.metrics_json:
            metrics = UsageMetrics.from_dict(json.loads(row.metrics_json))
        return Message(
            role=row.role,
            content=row.content,
            timestamp=datetime.fromisoformat(row.timestamp),
            metadata=json.loads(row.metadata_json) if row.metadata_json else {},
            metrics=metrics,
            message_type=row.message_type if row.message_type else "message",
        )
