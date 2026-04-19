"""Chat screen for Derek Agent Runner TUI."""

import asyncio

from textual.containers import ScrollableContainer, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Header, Label, Static

from ...core.agent_runner import AgentRunner
from ...core.config import get_config
from ...storage import Message
from ..widgets.chat_message import ChatMessage
from ..widgets.input_bar import InputBar


class ChatScreen(Screen):
    """Main chat screen."""

    DEFAULT_CSS = """
    ChatScreen {
        layout: vertical;
    }

    ChatScreen #chat-container {
        width: 100%;
        height: 1fr;
        padding: 1;
    }

    ChatScreen #chat-log {
        width: 100%;
        height: 100%;
        align: left bottom;
    }

    ChatScreen #status-bar {
        dock: top;
        height: 1;
        background: $surface-darken-1;
        color: $text-muted;
        content-align: center middle;
        text-style: bold;
    }

    ChatScreen #token-status-bar {
        height: 1;
        background: $surface-darken-1;
        color: $text-muted;
        content-align: center middle;
    }

    ChatScreen .empty-state {
        width: 100%;
        height: 100%;
        content-align: center middle;
        color: $text-muted;
        text-style: dim;
    }
    """

    agent_name = reactive("未選擇")
    is_generating = reactive(False)

    def __init__(self, runner: AgentRunner):
        """Initialize chat screen.

        Args:
            runner: Agent runner instance.
        """
        super().__init__()
        self.runner = runner
        self._current_streaming_message: ChatMessage | None = None
        self._generation_task: asyncio.Task | None = None

    def compose(self):
        """Compose the screen."""
        yield Header(show_clock=True)
        yield Label(id="status-bar")

        with Vertical(id="chat-container"):
            chat_log = ScrollableContainer(id="chat-log")
            chat_log.can_focus = False
            yield chat_log

        yield Label(id="token-status-bar")
        yield InputBar()

    def on_mount(self):
        """Called when screen is mounted."""
        self.update_status()
        self.run_worker(self.refresh_token_status())

        # Load default agent
        self.run_worker(self._load_default_agent())

    def watch_agent_name(self, name: str):
        """Watch for agent name changes."""
        self.update_status()
        self.run_worker(self.refresh_token_status())

    @staticmethod
    def format_token_status(
        context_tokens: int | None,
        cumulative_metrics,
    ) -> str:
        """Format token status bar content."""
        input_tokens = cumulative_metrics.input_tokens if cumulative_metrics else 0
        output_tokens = cumulative_metrics.output_tokens if cumulative_metrics else 0
        total_tokens = cumulative_metrics.total_tokens if cumulative_metrics else 0
        context_display = f"{context_tokens:,}" if context_tokens is not None else "-"
        return (
            f"Context: {context_display} | "
            f"Input: {input_tokens:,} | "
            f"Output: {output_tokens:,} | "
            f"Total: {total_tokens:,}"
        )

    def update_status(self):
        """Update status bar."""
        status = self.query_one("#status-bar", Label)
        if self.agent_name:
            status.update(f"目前 Agent: {self.agent_name}")
        else:
            status.update("未選擇 Agent")

    async def refresh_token_status(self, pending_message: str | None = None):
        """Refresh bottom token status bar."""
        token_status = self.query_one("#token-status-bar", Label)
        context_tokens = await self.runner.estimate_context_tokens(pending_message)
        cumulative_metrics = await self.runner.get_session_metrics()
        token_status.update(
            self.format_token_status(context_tokens, cumulative_metrics)
        )

    async def _load_default_agent(self):
        """Load default agent on startup."""
        try:
            # This will initialize with default agent from config
            agents = self.runner.list_available_agents()
            if agents:
                default_agent = agents[0]
                await self.runner.switch_agent(default_agent.id)
                self.agent_name = self.runner.get_current_agent_name()
                await self.refresh_token_status()

                # Show welcome message
                self.add_message(
                    "assistant",
                    f"你好！我是 **{self.agent_name}**。有什麼我可以幫你的嗎？",
                )
        except Exception as e:
            self.add_message("system", f"載入 Agent 時出錯: {e}")

    def add_message(self, role: str, content: str, mcp_phase: str | None = None, source_type: str | None = None) -> ChatMessage:
        """Add a message to the chat log.

        Args:
            role: Message role.
            content: Message content.
            mcp_phase: Optional MCP activity phase (start/success/error).
            source_type: Optional source type ("mcp" or "builtin").

        Returns:
            ChatMessage widget.
        """
        chat_log = self.query_one("#chat-log", ScrollableContainer)

        # Remove empty state if present
        empty_state = chat_log.query(".empty-state")
        for widget in empty_state:
            widget.remove()

        message_widget = ChatMessage(role, content, mcp_phase=mcp_phase, source_type=source_type)
        chat_log.mount(message_widget)
        chat_log.scroll_end(animate=False)
        return message_widget

    def add_mcp_activity_message(self, activity: dict) -> None:
        """Add MCP activity message to the chat log.

        Args:
            activity: MCP activity dictionary.
        """
        if get_config().settings.ui.mcp_activity_display_mode != "inline":
            return

        # Handle both old format (server_name) and new format (source_type, source_name)
        source_type = activity.get("source_type")  # "mcp" or "builtin"
        source_name = activity.get("source_name")  # server name or builtin source
        tool_name = activity.get("tool_name")

        # Fallback to old format for backward compatibility
        if source_type is None:
            source_name = activity.get("server_name")
            source_type = "mcp" if source_name else "builtin"

        phase = activity.get("phase")

        # Build rich message with context
        parts = []

        if phase == "start":
            parts.append("🔄 Calling")
        elif phase == "success":
            parts.append("✓ Retrieved")
        elif phase == "error":
            parts.append("✗ Failed")

        # Add tool identifier with source type indicator
        if tool_name and source_name:
            # Show icon based on source type
            source_icon = "🔧" if source_type == "builtin" else "📡"
            parts.append(f"{source_icon} {source_name}.{tool_name}")
        elif tool_name:
            parts.append(tool_name)
        else:
            parts.append(source_name or "unknown")

        # Add parameter names for start event
        if phase == "start":
            param_names = activity.get("param_names")
            if param_names:
                parts.append(f"({', '.join(param_names)})")

        # Add result preview for completed event (first 20 chars as requested)
        if phase == "success":
            result_preview = activity.get("result_preview")
            if result_preview:
                preview = result_preview[:20]  # First 20 chars as requested
                if len(result_preview) > 20:
                    preview += "..."
                parts.append(f"→ {preview}")

        # Add error details for error event
        if phase == "error":
            error = activity.get("error")
            if error:
                parts.append(f"- {str(error)[:40]}")

        content = " ".join(parts)
        self.add_message("system", content, mcp_phase=phase, source_type=source_type)

    def on_input_bar_message_sent(self, event: InputBar.MessageSent):
        """Handle message sent from input bar."""
        # Add user message
        self.add_message("user", event.content)
        self.run_worker(self.refresh_token_status(event.content))

        # Start generation
        self.run_worker(self._generate_response(event.content))

    async def _generate_response(self, message: str):
        """Generate response from agent.

        Args:
            message: User message.
        """
        if self.is_generating:
            return

        try:
            self.is_generating = True
            input_bar = self.query_one(InputBar)
            input_bar.set_generating(True)
            self._current_streaming_message = None

            # Stream response
            full_content = ""

            def on_chunk(chunk: str):
                nonlocal full_content
                full_content += chunk
                if self._current_streaming_message is None:
                    self._current_streaming_message = self.add_message("assistant", chunk)
                else:
                    current_content = self._current_streaming_message.content + chunk
                    self._current_streaming_message.update_content(current_content)
                chat_log = self.query_one("#chat-log", ScrollableContainer)
                chat_log.scroll_end(animate=False)

            def on_mcp_activity(activity: dict):
                self._current_streaming_message = None
                self.add_mcp_activity_message(activity)

            # Run agent with streaming
            await self.runner.send_message(
                message,
                stream_callback=on_chunk,
                mcp_activity_callback=on_mcp_activity,
            )

        except Exception as e:
            self.add_message("system", f"錯誤: {e}")
        finally:
            self.is_generating = False
            input_bar = self.query_one(InputBar)
            input_bar.set_generating(False)
            self._current_streaming_message = None
            await self.refresh_token_status()

    def on_input_bar_generation_stopped(self, event: InputBar.GenerationStopped):
        """Handle generation stopped."""
        if self._generation_task and not self._generation_task.done():
            self._generation_task.cancel()
        self.is_generating = False

    def on_input_bar_system_message(self, event: InputBar.SystemMessage):
        """Handle system message from command execution."""
        self.add_message("system", event.content)

    def on_input_bar_error_message(self, event: InputBar.ErrorMessage):
        """Handle error message from command execution."""
        self.add_message("system", f"❌ {event.content}")

    def action_switch_agent(self):
        """Action to switch agent."""
        self.app.push_screen("agent_select")

    def action_new_chat(self):
        """Action to start new chat."""
        self.run_worker(self._new_chat())

    async def _new_chat(self):
        """Start a new conversation."""
        try:
            session = await self.runner.start_conversation()
            # Clear chat log
            chat_log = self.query_one("#chat-log", ScrollableContainer)
            await chat_log.remove_children()
            await self.refresh_token_status()
            self.add_message("system", f"新對話已開始 (ID: {session.id[:8]}...)")
        except Exception as e:
            self.add_message("system", f"建立新對話失敗: {e}")

    def action_history(self):
        """Action to show conversation history."""
        # TODO: Implement history screen
        self.notify("對話歷史功能開發中...", severity="information")

    def action_settings(self):
        """Action to open settings."""
        # TODO: Implement settings screen
        self.notify("設定功能開發中...", severity="information")

    def action_quit(self):
        """Action to quit."""
        self.app.exit()

    def on_unmount(self):
        """Called when screen is unmounted."""
        # Cleanup any pending tasks
        if self._generation_task and not self._generation_task.done():
            self._generation_task.cancel()
