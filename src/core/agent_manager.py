"""Agent manager for Derek Agent Runner."""

import uuid
from pathlib import Path
from typing import Any

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.anthropic import Claude
from agno.models.openai import OpenAIChat

from ..storage import BaseStorage, Message, Session, UsageMetrics
from ..tools.web_search import create_search_tool
from ..tools.shell import create_shell_tool
from ..tools.file import create_file_tool
from ..tools.crawler import create_crawler_tool
from .config import AgentConfig, get_config, logger
from .mcp_client import MCPClientManager, get_mcp_manager
from .skills import build_agent_skills


class AgentInstance:
    """Wrapper for an Agno Agent with associated configuration."""

    def __init__(
        self,
        config: AgentConfig,
        agent: Agent,
        mcp_manager: MCPClientManager,
        user_id: str = "default",
    ):
        """Initialize agent instance.

        Args:
            config: Agent configuration.
            agent: Agno Agent instance.
            mcp_manager: MCP client manager.
            user_id: User identifier for memory persistence.
        """
        self.config = config
        self.agent = agent
        self.mcp_manager = mcp_manager
        self.user_id = user_id

    async def run(self, messages: list[dict] | str, **kwargs: Any) -> Any:
        """Run the agent with messages.

        Args:
            messages: List of message dicts with 'role' and 'content' keys,
                     or a single message string for backward compatibility.
            **kwargs: Additional arguments for agent.run.

        Returns:
            Agent response.
        """
        # Ensure user_id is passed for memory persistence
        if "user_id" not in kwargs:
            kwargs["user_id"] = self.user_id
        return await self.agent.arun(messages, **kwargs)

    def run_stream(self, messages: list[dict] | str, **kwargs: Any) -> Any:
        """Run the agent with streaming response.

        Args:
            messages: List of message dicts with 'role' and 'content' keys,
                     or a single message string for backward compatibility.
            **kwargs: Additional arguments for agent.arun.

        Returns:
            Streaming response (async generator).
        """
        # Ensure user_id is passed for memory persistence
        if "user_id" not in kwargs:
            kwargs["user_id"] = self.user_id
        return self.agent.arun(messages, stream=True, **kwargs)

    async def cleanup(self) -> None:
        """Cleanup resources."""
        await self.mcp_manager.close_all()

    def get_mcp_status(self) -> dict[str, dict]:
        """Get MCP server status for this agent.

        Returns:
            Dict mapping server name to status info.
        """
        return self.mcp_manager.get_server_status()

    def disable_mcp_server(self, name: str) -> bool:
        """Temporarily disable an MCP server for this agent.

        Args:
            name: MCP server name.

        Returns:
            True if server was disabled.
        """
        return self.mcp_manager.disable_server(name)

    def enable_mcp_server(self, name: str) -> bool:
        """Re-enable a disabled MCP server for this agent.

        Args:
            name: MCP server name.

        Returns:
            True if server was enabled.
        """
        return self.mcp_manager.enable_server(name)

    def get_skills(self) -> list[dict[str, str]]:
        """Get available file-based skills for this agent."""
        skills = getattr(self.agent, "skills", None)
        if skills is None:
            return []

        result: list[dict[str, str]] = []
        for skill in skills.get_all_skills():
            result.append(
                {
                    "name": skill.name,
                    "description": skill.description,
                }
            )
        return result

    def get_memories(self) -> list[dict[str, Any]]:
        """Get user memories for this agent.

        Returns:
            List of memory dicts with 'memory' and 'created_at' keys.
        """
        try:
            memories = self.agent.get_user_memories(user_id=self.user_id)
            return [
                {
                    "memory": getattr(m, "memory", str(m)),
                    "created_at": getattr(m, "created_at", None),
                }
                for m in memories
            ]
        except Exception as e:
            return []


def parse_model_string(model_str: str) -> tuple[str, str]:
    """Parse a model string like 'openai:gpt-4o'.

    Args:
        model_str: Model string in format 'provider:model_id'.

    Returns:
        Tuple of (provider, model_id).
    """
    if ":" in model_str:
        provider, model_id = model_str.split(":", 1)
        return provider.lower(), model_id
    return "openai", model_str


def create_model(provider: str, model_id: str, **kwargs: Any) -> Any:
    """Create a model instance.

    Args:
        provider: Model provider (openai, anthropic, minimax, etc.).
        model_id: Model identifier.
        **kwargs: Additional model parameters.

    Returns:
        Model instance.
    """
    if provider == "openai":
        return OpenAIChat(id=model_id, **kwargs)
    elif provider in ("anthropic", "claude"):
        return Claude(id=model_id, **kwargs)
    else:
        # Try providers.yaml for any other provider (minimax, etc.)
        try:
            from .providers import create_model_from_provider
            return create_model_from_provider(provider, model_id)
        except Exception as e:
            logger.warning(f"Provider '{provider}' lookup failed: {e}. Falling back to OpenAI.")
            return OpenAIChat(id=model_id, **kwargs)


def resolve_agno_sqlite_db_path() -> str | None:
    """Resolve SQLite database path for Agno memory when available."""
    storage_config = get_config().settings.storage
    if storage_config.type != "sqlite":
        return None

    if storage_config.path:
        return storage_config.path

    if storage_config.url and storage_config.url.startswith("sqlite:///"):
        return str(Path(storage_config.url.removeprefix("sqlite:///")))

    return None


class AgentManager:
    """Manager for creating and managing agent instances."""

    def __init__(
        self,
        mcp_manager: MCPClientManager | None = None,
    ):
        """Initialize agent manager.

        Args:
            mcp_manager: Optional MCP client manager.
        """
        self.mcp_manager = mcp_manager or get_mcp_manager()
        self._active_instances: dict[str, AgentInstance] = {}

    async def create_agent(self, config: AgentConfig) -> AgentInstance:
        """Create an agent instance from configuration.

        Args:
            config: Agent configuration.

        Returns:
            AgentInstance.
        """
        # Parse model
        provider, model_id = parse_model_string(config.model)
        model = create_model(provider, model_id)

        agent_skills = build_agent_skills(config)

        tools = []

        # Setup MCP servers
        if config.mcp_servers:
            mcp_tools = await self.mcp_manager.setup_from_config(config.mcp_servers)
            tools.extend(mcp_tools)

        # Setup web search tool
        global_search_config = get_config().settings.web_search
        search_tool = create_search_tool(global_search_config, config.search)
        if search_tool is not None:
            tools.append(search_tool)
            logger.info(f"Enabled web search ({config.search.provider or global_search_config.provider}) for agent: {config.id}")

        # Setup shell tool
        shell_tool = create_shell_tool(config.shell, working_dir=config.working_dir)
        if shell_tool is not None:
            tools.append(shell_tool)
            logger.info(f"Enabled shell tool for agent: {config.id}")

        # Setup file tool
        file_tool = create_file_tool(config.file, working_dir=config.working_dir)
        if file_tool is not None:
            tools.append(file_tool)
            logger.info(f"Enabled file tool for agent: {config.id}")

        # Setup crawler tool
        crawler_tool = create_crawler_tool(config.crawler)
        if crawler_tool is not None:
            tools.append(crawler_tool)
            logger.info(f"Enabled crawler tool for agent: {config.id}")

        # Setup Agno memory database
        db_path = resolve_agno_sqlite_db_path()
        agno_db = SqliteDb(db_file=db_path) if db_path else None

        # Create Agno Agent with memory enabled
        agent = Agent(
            model=model,
            description=config.description or config.system_prompt,
            instructions=config.system_prompt,
            skills=agent_skills,
            tools=tools if tools else None,
            markdown=True,
            add_history_to_context=True,
            num_history_runs=10,
            db=agno_db,
            enable_agentic_memory=True,
            add_datetime_to_context=config.add_datetime_to_context,
            timezone_identifier="Asia/Taipei",
        )

        instance = AgentInstance(
            config=config,
            agent=agent,
            mcp_manager=self.mcp_manager,
            user_id=get_config().settings.user_id,
        )

        self._active_instances[config.id] = instance
        logger.info(f"Created agent instance: {config.id}")
        return instance

    def get_agent(self, agent_id: str) -> AgentInstance | None:
        """Get an active agent instance.

        Args:
            agent_id: Agent ID.

        Returns:
            AgentInstance or None.
        """
        return self._active_instances.get(agent_id)

    async def load_agent(self, agent_id: str) -> AgentInstance | None:
        """Load an agent by ID from configuration.

        Args:
            agent_id: Agent ID.

        Returns:
            AgentInstance or None if not found.
        """
        # Check if already loaded
        if agent_id in self._active_instances:
            return self._active_instances[agent_id]

        # Load from config
        config = get_config().get_agent(agent_id)
        if not config:
            logger.error(f"Agent not found: {agent_id}")
            return None

        return await self.create_agent(config)

    def list_agents(self) -> list[AgentConfig]:
        """List all available agent configurations.

        Returns:
            List of AgentConfig.
        """
        return get_config().agents

    async def unload_agent(self, agent_id: str) -> bool:
        """Unload an agent instance.

        Args:
            agent_id: Agent ID.

        Returns:
            True if agent was found and unloaded.
        """
        instance = self._active_instances.get(agent_id)
        if instance:
            await instance.cleanup()
            del self._active_instances[agent_id]
            logger.info(f"Unloaded agent: {agent_id}")
            return True
        return False

    async def unload_all(self) -> None:
        """Unload all agent instances."""
        for instance in self._active_instances.values():
            await instance.cleanup()
        self._active_instances.clear()


class ConversationManager:
    """Manages conversations/sessions for agents."""

    def __init__(self, storage: BaseStorage):
        """Initialize conversation manager.

        Args:
            storage: Storage instance.
        """
        self.storage = storage

    async def create_session(
        self, agent_id: str, title: str | None = None
    ) -> Session:
        """Create a new conversation session.

        Args:
            agent_id: Agent ID.
            title: Optional session title.

        Returns:
            New Session.
        """
        session_id = str(uuid.uuid4())
        session = Session(
            id=session_id,
            agent_id=agent_id,
            title=title or "新對話",
        )
        await self.storage.create_session(session)
        logger.info(f"Created session: {session_id} for agent: {agent_id}")
        return session

    async def get_session(self, session_id: str) -> Session | None:
        """Get a session by ID.

        Args:
            session_id: Session ID.

        Returns:
            Session or None.
        """
        return await self.storage.get_session(session_id)

    async def list_sessions(
        self, agent_id: str | None = None, limit: int = 50
    ) -> list[Session]:
        """List sessions.

        Args:
            agent_id: Optional agent ID filter.
            limit: Maximum number of results.

        Returns:
            List of sessions.
        """
        return await self.storage.list_sessions(agent_id, limit)

    async def add_message(self, session_id: str, role: str, content: str, metrics: "UsageMetrics | None" = None) -> Message:
        """Add a message to a session.

        Args:
            session_id: Session ID.
            role: Message role (user/assistant/system).
            content: Message content.
            metrics: Optional token usage metrics.

        Returns:
            Created Message.
        """
        message = Message(role=role, content=content, metrics=metrics)
        await self.storage.add_message(session_id, message)
        return message

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: Session ID.

        Returns:
            True if deleted.
        """
        return await self.storage.delete_session(session_id)


# Global instances
_agent_manager: AgentManager | None = None
_conversation_manager: ConversationManager | None = None


def get_agent_manager() -> AgentManager:
    """Get global agent manager."""
    global _agent_manager
    if _agent_manager is None:
        _agent_manager = AgentManager()
    return _agent_manager


def get_conversation_manager(storage: BaseStorage | None = None) -> ConversationManager:
    """Get global conversation manager."""
    global _conversation_manager
    if _conversation_manager is None:
        if storage is None:
            raise ValueError("Storage required for conversation manager")
        _conversation_manager = ConversationManager(storage)
    return _conversation_manager
