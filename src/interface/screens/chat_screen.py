"""Chat screen for Derek Agent Runner TUI."""

import asyncio

from textual.containers import ScrollableContainer, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Header, Label, Static
from textual.binding import Binding

from ...core.agent_runner import AgentRunner
from ...core.config import get_config
from ...storage import Message
from ..widgets.chat_message import ChatMessage
from ..widgets.input_bar import InputBar
from .history_screen import HistoryScreen


class ChatScreen(Screen):
    """Main chat screen."""

    BINDINGS = [
        Binding("ctrl+c", "compress", "壓縮對話", show=False),
    ]

    DEFAULT_CSS = """
    ChatScreen #compression-notice {
        dock: top;
        height: 1;
        background: $warning-darken-2;
        color: $text;
        content-align: center middle;
        text-style: bold;
    }

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

    ChatScreen #compression-notice.hidden {
        display: none;
    }
    """

    agent_name = reactive("未選擇")
    is_generating = reactive(False)
    compression_suggested = reactive(False)

    def __init__(self, runner: AgentRunner):
        """Initialize chat screen.

        Args:
            runner: Agent runner instance.
        """
        super().__init__()
        self.runner = runner
        self._current_streaming_message: ChatMessage | None = None
        self._generation_task: asyncio.Task | None = None
        self._compression_notice: Label | None = None

    def compose(self):
        """Compose the screen."""
        yield Header(show_clock=True)
        yield Label(id="status-bar")
        yield Label(id="compression-notice", classes="hidden")

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

    def watch_compression_suggested(self, suggested: bool):
        """Watch for compression suggestion changes."""
        notice = self.query_one("#compression-notice", Label)
        if suggested:
            notice.remove_class("hidden")
            notice.update("⚠ 對話內容已達上下文上限的 50%，建議壓縮以釋放空間 (Alt+C)")
        else:
            notice.add_class("hidden")

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

        # Check if compression is needed
        await self._check_compression_status(pending_message)

    async def _check_compression_status(self, pending_message: str | None = None):
        """Check if compression suggestion should be shown."""
        try:
            compression_status = await self.runner.check_compression_needed(pending_message)
            if compression_status["enabled"] and compression_status["needed"]:
                # Only suggest if auto_trigger is enabled
                config = self.runner.get_compression_config()
                if config["auto_trigger"]:
                    self.compression_suggested = True
                else:
                    self.compression_suggested = False
            else:
                self.compression_suggested = False
        except Exception:
            self.compression_suggested = False

    def action_compress(self):
        """Action to compress conversation."""
        self.run_worker(self._compress_conversation())

    async def _compress_conversation(self):
        """Perform conversation compression."""
        try:
            self.add_message("system", "🔄 正在壓縮對話內容...")
            result = await self.runner.compress_conversation()

            if result["success"]:
                self.compression_suggested = False
                msg_count = result["message_count"]
                self.add_message("system", f"✅ 對話已壓縮（{msg_count} 則訊息已摘要）")
                await self.refresh_token_status()
            else:
                error = result.get("error", "未知錯誤")
                self.add_message("system", f"❌ 壓縮失敗: {error}")

        except Exception as e:
            self.add_message("system", f"❌ 壓縮時發生錯誤: {e}")

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

    def add_message(self, role: str, content: str, mcp_phase: str | None = None, source_type: str | None = None, message_type: str | None = None) -> ChatMessage:
        """Add a message to the chat log.

        Args:
            role: Message role.
            content: Message content.
            mcp_phase: Optional MCP activity phase (start/success/error).
            source_type: Optional source type ("mcp" or "builtin").
            message_type: Optional message type (message, summary, archived).

        Returns:
            ChatMessage widget.
        """
        chat_log = self.query_one("#chat-log", ScrollableContainer)

        # Remove empty state if present
        empty_state = chat_log.query(".empty-state")
        for widget in empty_state:
            widget.remove()

        message_widget = ChatMessage(role, content, mcp_phase=mcp_phase, source_type=source_type, message_type=message_type)
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
        self.run_worker(self._show_history())

    async def _show_history(self):
        """Show history screen and handle selection."""
        agent_name = self.runner.get_current_agent_name() or "未選擇"
        history_screen = HistoryScreen(self.runner, agent_name)

        def on_dismiss(session):
            if session:
                self.run_worker(self._load_conversation(session))

        self.app.push_screen(history_screen, on_dismiss)

    async def _load_conversation(self, session):
        """Load a conversation and restore messages.

        Args:
            session: Session object to load.
        """
        try:
            # Load the conversation via runner
            loaded_session = await self.runner.load_conversation(session.id)
            if not loaded_session:
                self.notify("載入對話失敗", severity="error")
                return

            # Clear current chat log
            chat_log = self.query_one("#chat-log", ScrollableContainer)
            await chat_log.remove_children()

            # Update agent name display
            self.agent_name = self.runner.get_current_agent_name() or "未選擇"

            # Restore messages
            for msg in loaded_session.messages:
                if msg.role in ("user", "assistant"):
                    self.add_message(msg.role, msg.content, message_type=msg.message_type)
                elif msg.role == "system":
                    self.add_message("system", msg.content, message_type=msg.message_type)

            # Refresh token status
            await self.refresh_token_status()

            # Show confirmation
            self.notify(f"已載入對話: {loaded_session.title or '未命名'}", severity="information")

        except Exception as e:
            self.notify(f"載入對話失敗: {e}", severity="error")

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
