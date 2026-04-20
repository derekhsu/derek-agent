"""Agent runner for Derek Agent Runner - main orchestration."""

import asyncio
from typing import Any, AsyncIterator, Callable

from agno.agent import RunEvent
from agno.utils.tokens import count_text_tokens

from ..storage import BaseStorage, Message, Session, UsageMetrics, create_storage
from .agent_manager import AgentManager, ConversationManager, get_agent_manager, get_conversation_manager, parse_model_string
from .config import get_config, logger


class AgentRunner:
    """Main runner for executing agent conversations."""

    @staticmethod
    def _build_usage_metrics(agno_metrics: Any) -> UsageMetrics | None:
        """Build UsageMetrics from Agno metrics object."""
        if not agno_metrics:
            return None

        return UsageMetrics(
            input_tokens=getattr(agno_metrics, "input_tokens", 0),
            output_tokens=getattr(agno_metrics, "output_tokens", 0),
            total_tokens=getattr(agno_metrics, "total_tokens", 0),
            cost=getattr(agno_metrics, "cost", None),
            audio_input_tokens=getattr(agno_metrics, "audio_input_tokens", 0),
            audio_output_tokens=getattr(agno_metrics, "audio_output_tokens", 0),
            cache_read_tokens=getattr(agno_metrics, "cache_read_tokens", 0),
            cache_write_tokens=getattr(agno_metrics, "cache_write_tokens", 0),
            reasoning_tokens=getattr(agno_metrics, "reasoning_tokens", 0),
        )

    def _get_current_model_id(self) -> str:
        """Get current model id for token estimation."""
        if not self._current_agent_id:
            return "gpt-4o"

        agent_config = self.config.get_agent(self._current_agent_id)
        if not agent_config:
            return "gpt-4o"

        _, model_id = parse_model_string(agent_config.model)
        return model_id

    def __init__(
        self,
        agent_manager: AgentManager | None = None,
        conversation_manager: ConversationManager | None = None,
        storage: BaseStorage | None = None,
    ):
        """Initialize agent runner.

        Args:
            agent_manager: Optional agent manager.
            conversation_manager: Optional conversation manager.
            storage: Optional storage instance.
        """
        self.config = get_config()
        self.storage = storage or create_storage(self.config.settings.storage)
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

    def _resolve_tool_info(self, raw_tool_name: str | None) -> tuple[str | None, str | None, str]:
        """Resolve tool name to source and display name.

        Args:
            raw_tool_name: Raw tool name from Agno.

        Returns:
            Tuple of (source_type, source_name, tool_name).
            source_type: "mcp", "builtin", or None
        """
        if not raw_tool_name:
            return None, None, ""

        # Check if it's an MCP tool first
        server_name, tool_name = self.agent_manager.mcp_manager.resolve_tool_name(raw_tool_name)
        if server_name is not None:
            return "mcp", server_name, tool_name

        # Check for built-in tools by prefix patterns
        builtin_prefixes = {
            "shell_tools_": ("shell", "shell"),
            "file_tools_": ("file", "file"),
            "trafilatura_tools_": ("crawler", "trafilatura"),
            "duckduckgo_": ("web_search", "duckduckgo"),
            "tavily_": ("web_search", "tavily"),
            "websearch_": ("web_search", "websearch"),
        }

        for prefix, (source_name, _) in builtin_prefixes.items():
            if raw_tool_name.startswith(prefix):
                tool_name = raw_tool_name[len(prefix):]
                return "builtin", source_name, tool_name

        # Unknown tool - treat as built-in with generic name
        return "builtin", "builtin", raw_tool_name

    def _build_tool_activity(
        self,
        raw_tool_name: str | None,
        event_name: str,
        tool: Any,
        chunk: Any,
    ) -> dict[str, Any] | None:
        """Build tool activity info for display.

        Args:
            raw_tool_name: Raw tool name from Agno.
            event_name: Event type (started/completed/error).
            tool: Tool object from Agno.
            chunk: Response chunk from Agno.

        Returns:
            Activity dict or None if not a trackable tool.
        """
        source_type, source_name, tool_name = self._resolve_tool_info(raw_tool_name)

        if source_type is None:
            return None

        # Determine phase
        if event_name == RunEvent.tool_call_started.value:
            phase = "start"
        elif event_name == RunEvent.tool_call_completed.value:
            phase = "success"
        else:  # error
            phase = "error"

        activity: dict[str, Any] = {
            "phase": phase,
            "tool_name": tool_name,
            "source_type": source_type,
            "source_name": source_name,
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
                result_str = str(result)[:20]  # First 20 chars as requested
                activity["result_preview"] = result_str

        # Collect error info
        if event_name == RunEvent.tool_call_error.value:
            activity["error"] = getattr(chunk, "error", None)

        return activity

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

        # Get agent instance
        agent_instance = self.agent_manager.get_agent(self._current_agent_id)
        if not agent_instance:
            raise RuntimeError(f"Agent not loaded: {self._current_agent_id}")

        # Load conversation history and build messages list
        history = await self.get_conversation_history()
        messages = []
        for msg in history:
            if msg.role in ("user", "assistant"):
                messages.append({"role": msg.role, "content": msg.content})
        # Add current user message
        messages.append({"role": "user", "content": message})

        # Save user message (no metrics for user message)
        await self.conversation_manager.add_message(
            self._current_session.id, "user", message
        )

        # Run agent and capture metrics
        response_metrics = None

        if stream_callback:
            # Streaming mode
            response_text = ""
            async for chunk in agent_instance.run_stream(messages, stream_events=True):
                event_name = getattr(chunk, "event", None)
                if event_name == RunEvent.run_content.value:
                    content = getattr(chunk, "content", None)
                    if content:
                        response_text += content
                        stream_callback(content)
                    continue

                if event_name == RunEvent.run_completed.value:
                    completed_content = getattr(chunk, "content", None)
                    if completed_content and not response_text:
                        response_text = str(completed_content)
                        stream_callback(response_text)
                    response_metrics = self._build_usage_metrics(
                        getattr(chunk, "metrics", None)
                    )
                    continue

                if mcp_activity_callback and event_name in {
                    RunEvent.tool_call_started.value,
                    RunEvent.tool_call_completed.value,
                    RunEvent.tool_call_error.value,
                }:
                    tool = getattr(chunk, "tool", None)
                    raw_tool_name = getattr(tool, "tool_name", None)
                    activity = self._build_tool_activity(
                        raw_tool_name, event_name, tool, chunk
                    )
                    if activity:
                        mcp_activity_callback(activity)

            # For streaming mode, we need to get metrics from the response object
            # Note: Agno streaming doesn't provide metrics in chunks, metrics are in the final response
        else:
            # Non-streaming mode
            response = await agent_instance.run(messages)
            response_text = getattr(response, "content", str(response))
            response_metrics = self._build_usage_metrics(getattr(response, "metrics", None))

        # Save assistant message with metrics
        await self.conversation_manager.add_message(
            self._current_session.id, "assistant", response_text, metrics=response_metrics
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

    async def estimate_context_tokens(self, pending_message: str | None = None) -> int:
        """Estimate context tokens for the current conversation."""
        history = await self.get_conversation_history()
        model_id = self._get_current_model_id()
        total = 0

        for msg in history:
            if msg.role in ("user", "assistant"):
                total += count_text_tokens(f"{msg.role}: {msg.content}", model_id)

        if pending_message:
            total += count_text_tokens(f"user: {pending_message}", model_id)

        return total

    async def get_session_metrics(self) -> "UsageMetrics | None":
        """Get total token usage metrics for current session.

        Returns:
            UsageMetrics with aggregated totals, or None if no session.
        """
        if not self._current_session:
            return None

        session = await self.conversation_manager.get_session(self._current_session.id)
        if session:
            return session.get_total_metrics()
        return None

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

    def get_current_agent_skills(self) -> list[dict[str, str]] | None:
        """Get available skills for the current agent."""
        if not self._current_agent_id:
            return None
        agent_instance = self.agent_manager.get_agent(self._current_agent_id)
        if not agent_instance:
            return None
        return agent_instance.get_skills()

    def get_current_agent_memories(self) -> list[dict[str, Any]] | None:
        """Get user memories for the current agent."""
        if not self._current_agent_id:
            return None
        agent_instance = self.agent_manager.get_agent(self._current_agent_id)
        if not agent_instance:
            return None
        return agent_instance.get_memories()


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
