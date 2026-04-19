"""Agent runner for Derek Agent Runner - main orchestration."""

import asyncio
from typing import Any, AsyncIterator, Callable

from agno.agent import RunEvent

from ..storage import Message, Session, SQLiteStorage
from .agent_manager import AgentManager, ConversationManager, get_agent_manager, get_conversation_manager
from .config import get_config, logger
from .mcp_client import get_mcp_manager
from .skill_registry import get_skill_registry


class AgentRunner:
    """Main runner for executing agent conversations."""

    def __init__(
        self,
        agent_manager: AgentManager | None = None,
        conversation_manager: ConversationManager | None = None,
        storage: SQLiteStorage | None = None,
    ):
        """Initialize agent runner.

        Args:
            agent_manager: Optional agent manager.
            conversation_manager: Optional conversation manager.
            storage: Optional storage instance.
        """
        self.config = get_config()
        self.storage = storage or SQLiteStorage(self.config.settings.storage.path)
        self.agent_manager = agent_manager or get_agent_manager()
        self.conversation_manager = conversation_manager or get_conversation_manager(self.storage)

        self._current_agent_id: str | None = None
        self._current_session: Session | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the runner."""
        if self._initialized:
            return

        await self.storage.initialize()
        self._initialized = True
        logger.info("Agent runner initialized")

    async def shutdown(self) -> None:
        """Shutdown the runner."""
        await self.agent_manager.unload_all()
        await self.storage.close()
        logger.info("Agent runner shutdown")

    async def switch_agent(self, agent_id: str) -> bool:
        """Switch to a different agent.

        Args:
            agent_id: Agent ID to switch to.

        Returns:
            True if successful.
        """
        # Load the agent
        instance = await self.agent_manager.load_agent(agent_id)
        if not instance:
            return False

        self._current_agent_id = agent_id
        self._current_session = None  # Reset session when switching agent
        logger.info(f"Switched to agent: {agent_id}")
        return True

    async def start_conversation(self, title: str | None = None) -> Session:
        """Start a new conversation.

        Args:
            title: Optional conversation title.

        Returns:
            New session.
        """
        if not self._current_agent_id:
            # Use default agent
            default_agent = self.config.settings.default_agent
            await self.switch_agent(default_agent)

        session = await self.conversation_manager.create_session(
            self._current_agent_id, title
        )
        self._current_session = session
        return session

    async def load_conversation(self, session_id: str) -> Session | None:
        """Load an existing conversation.

        Args:
            session_id: Session ID.

        Returns:
            Session or None.
        """
        session = await self.conversation_manager.get_session(session_id)
        if session:
            self._current_session = session
            self._current_agent_id = session.agent_id
            # Ensure agent is loaded
            await self.agent_manager.load_agent(session.agent_id)
        return session

    async def send_message(
        self,
        message: str,
        stream_callback: Callable[[str], None] | None = None,
        mcp_activity_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> str:
        """Send a message and get response.

        Args:
            message: User message.
            stream_callback: Optional callback for streaming chunks.
            mcp_activity_callback: Optional callback for MCP activity events.

        Returns:
            Full response text.
        """
        if not self._current_session:
            await self.start_conversation()

        if not self._current_agent_id:
            raise RuntimeError("No agent selected")

        # Save user message
        await self.conversation_manager.add_message(
            self._current_session.id, "user", message
        )

        # Get agent instance
        agent_instance = self.agent_manager.get_agent(self._current_agent_id)
        if not agent_instance:
            raise RuntimeError(f"Agent not loaded: {self._current_agent_id}")

        # Run agent
        if stream_callback:
            # Streaming mode
            response_text = ""
            async for chunk in agent_instance.run_stream(message, stream_events=True):
                event_name = getattr(chunk, "event", None)
                if event_name == RunEvent.run_content.value:
                    content = getattr(chunk, "content", None)
                    if content:
                        response_text += content
                        stream_callback(content)
                    continue

                if mcp_activity_callback and event_name in {
                    RunEvent.tool_call_started.value,
                    RunEvent.tool_call_completed.value,
                    RunEvent.tool_call_error.value,
                }:
                    tool = getattr(chunk, "tool", None)
                    raw_tool_name = getattr(tool, "tool_name", None)
                    server_name, tool_name = self.agent_manager.mcp_manager.resolve_tool_name(raw_tool_name)
                    if server_name is not None:
                        activity: dict[str, Any] = {
                            "phase": "start" if event_name == RunEvent.tool_call_started.value else "success",
                            "server_name": server_name,
                            "tool_name": tool_name,
                        }
                        # Collect parameter names for start event
                        if event_name == RunEvent.tool_call_started.value:
                            parameters = getattr(tool, "parameters", None) or getattr(tool, "arguments", None)
                            if parameters and isinstance(parameters, dict):
                                activity["param_names"] = list(parameters.keys())
                        # Collect result preview for completed event
                        if event_name == RunEvent.tool_call_completed.value:
                            result = getattr(chunk, "result", None) or getattr(chunk, "content", None)
                            if result:
                                result_str = str(result)[:50]  # First 50 chars
                                activity["result_preview"] = result_str
                        if event_name == RunEvent.tool_call_error.value:
                            activity["phase"] = "error"
                            activity["error"] = getattr(chunk, "error", None)
                        mcp_activity_callback(activity)
        else:
            # Non-streaming mode
            response = await agent_instance.run(message)
            response_text = getattr(response, "content", str(response))

        # Save assistant message
        await self.conversation_manager.add_message(
            self._current_session.id, "assistant", response_text
        )

        return response_text

    async def get_conversation_history(self) -> list[Message]:
        """Get current conversation history.

        Returns:
            List of messages.
        """
        if not self._current_session:
            return []

        session = await self.conversation_manager.get_session(self._current_session.id)
        if session:
            return session.messages
        return []

    def get_current_agent_name(self) -> str | None:
        """Get current agent name.

        Returns:
            Agent name or None.
        """
        if not self._current_agent_id:
            return None

        config = self.config.get_agent(self._current_agent_id)
        return config.name if config else None

    def list_available_agents(self):
        """List all available agents.

        Returns:
            List of AgentConfig.
        """
        return self.agent_manager.list_agents()

    async def list_conversations(self, limit: int = 50) -> list[Session]:
        """List conversations.

        Args:
            limit: Maximum number of results.

        Returns:
            List of sessions.
        """
        return await self.conversation_manager.list_sessions(
            self._current_agent_id, limit
        )

    def get_mcp_status(self) -> dict[str, dict] | None:
        """Get MCP server status for current agent.

        Returns:
            Dict mapping server name to status, or None if no agent loaded.
        """
        if not self._current_agent_id:
            return None
        agent_instance = self.agent_manager.get_agent(self._current_agent_id)
        if not agent_instance:
            return None
        return agent_instance.get_mcp_status()

    def disable_mcp_server(self, name: str) -> bool:
        """Disable an MCP server for current agent.

        Args:
            name: MCP server name.

        Returns:
            True if successful.
        """
        if not self._current_agent_id:
            return False
        agent_instance = self.agent_manager.get_agent(self._current_agent_id)
        if not agent_instance:
            return False
        return agent_instance.disable_mcp_server(name)

    def enable_mcp_server(self, name: str) -> bool:
        """Enable a disabled MCP server for current agent.

        Args:
            name: MCP server name.

        Returns:
            True if successful.
        """
        if not self._current_agent_id:
            return False
        agent_instance = self.agent_manager.get_agent(self._current_agent_id)
        if not agent_instance:
            return False
        return agent_instance.enable_mcp_server(name)


# Global runner instance
_runner: AgentRunner | None = None


async def get_runner() -> AgentRunner:
    """Get global agent runner (initialized)."""
    global _runner
    if _runner is None:
        _runner = AgentRunner()
        await _runner.initialize()
    return _runner


def reset_runner() -> None:
    """Reset global runner."""
    global _runner
    _runner = None
