"""Base storage interface for Derek Agent Runner."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class UsageMetrics:
    """Token usage metrics for a conversation turn."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost: float | None = None

    # Optional detailed metrics from Agno
    audio_input_tokens: int = 0
    audio_output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    reasoning_tokens: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
        }
        if self.cost is not None:
            result["cost"] = self.cost
        if self.audio_input_tokens:
            result["audio_input_tokens"] = self.audio_input_tokens
        if self.audio_output_tokens:
            result["audio_output_tokens"] = self.audio_output_tokens
        if self.cache_read_tokens:
            result["cache_read_tokens"] = self.cache_read_tokens
        if self.cache_write_tokens:
            result["cache_write_tokens"] = self.cache_write_tokens
        if self.reasoning_tokens:
            result["reasoning_tokens"] = self.reasoning_tokens
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UsageMetrics":
        """Create from dictionary."""
        return cls(
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            total_tokens=data.get("total_tokens", 0),
            cost=data.get("cost"),
            audio_input_tokens=data.get("audio_input_tokens", 0),
            audio_output_tokens=data.get("audio_output_tokens", 0),
            cache_read_tokens=data.get("cache_read_tokens", 0),
            cache_write_tokens=data.get("cache_write_tokens", 0),
            reasoning_tokens=data.get("reasoning_tokens", 0),
        )

    def __add__(self, other: "UsageMetrics") -> "UsageMetrics":
        """Add two metrics together."""
        return UsageMetrics(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            cost=(self.cost or 0) + (other.cost or 0) if self.cost or other.cost else None,
            audio_input_tokens=self.audio_input_tokens + other.audio_input_tokens,
            audio_output_tokens=self.audio_output_tokens + other.audio_output_tokens,
            cache_read_tokens=self.cache_read_tokens + other.cache_read_tokens,
            cache_write_tokens=self.cache_write_tokens + other.cache_write_tokens,
            reasoning_tokens=self.reasoning_tokens + other.reasoning_tokens,
        )


class Message:
    """Represents a conversation message."""

    def __init__(
        self,
        role: str,
        content: str,
        timestamp: datetime | None = None,
        metadata: dict[str, Any] | None = None,
        metrics: UsageMetrics | None = None,
        message_type: str = "message",  # message, summary, archived
    ):
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.now()
        self.metadata = metadata or {}
        self.metrics = metrics
        self.message_type = message_type

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "message_type": self.message_type,
        }
        if self.metrics:
            result["metrics"] = self.metrics.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Message":
        """Create from dictionary."""
        metrics_data = data.get("metrics")
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
            metrics=UsageMetrics.from_dict(metrics_data) if metrics_data else None,
            message_type=data.get("message_type", "message"),
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
        is_compressed: bool = False,
    ):
        self.id = id
        self.agent_id = agent_id
        self.title = title
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.messages = messages or []
        self.metadata = metadata or {}
        self.is_compressed = is_compressed

    def add_message(self, message: Message) -> None:
        """Add a message to the session."""
        self.messages.append(message)
        self.updated_at = datetime.now()

    def get_total_metrics(self) -> UsageMetrics:
        """Calculate total metrics across all messages in the session."""
        total = UsageMetrics()
        for message in self.messages:
            if message.metrics:
                total = total + message.metrics
        return total

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
            "is_compressed": self.is_compressed,
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
            is_compressed=data.get("is_compressed", False),
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
