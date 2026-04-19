"""Base storage interface for Derek Agent Runner."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any


class Message:
    """Represents a conversation message."""

    def __init__(
        self,
        role: str,
        content: str,
        timestamp: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.now()
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Message":
        """Create from dictionary."""
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
        )


class Session:
    """Represents a conversation session."""

    def __init__(
        self,
        id: str,
        agent_id: str,
        title: str | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        messages: list[Message] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.id = id
        self.agent_id = agent_id
        self.title = title
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.messages = messages or []
        self.metadata = metadata or {}

    def add_message(self, message: Message) -> None:
        """Add a message to the session."""
        self.messages.append(message)
        self.updated_at = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "title": self.title,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "messages": [m.to_dict() for m in self.messages],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Session":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            agent_id=data["agent_id"],
            title=data.get("title"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            messages=[Message.from_dict(m) for m in data.get("messages", [])],
            metadata=data.get("metadata", {}),
        )


class BaseStorage(ABC):
    """Abstract base class for storage implementations."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize storage (create tables, etc.)."""
        pass

    @abstractmethod
    async def create_session(self, session: Session) -> Session:
        """Create a new session."""
        pass

    @abstractmethod
    async def get_session(self, session_id: str) -> Session | None:
        """Get a session by ID."""
        pass

    @abstractmethod
    async def list_sessions(
        self, agent_id: str | None = None, limit: int = 50
    ) -> list[Session]:
        """List sessions, optionally filtered by agent."""
        pass

    @abstractmethod
    async def update_session(self, session: Session) -> Session:
        """Update a session."""
        pass

    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        pass

    @abstractmethod
    async def add_message(self, session_id: str, message: Message) -> Message:
        """Add a message to a session."""
        pass

    @abstractmethod
    async def get_messages(self, session_id: str) -> list[Message]:
        """Get all messages in a session."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close storage connection."""
        pass
