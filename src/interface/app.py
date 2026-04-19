"""Main TUI application for Derek Agent Runner."""

import asyncio
import logging

from textual.app import App, ComposeResult
from textual.binding import Binding

from ..core.agent_runner import AgentRunner, get_runner
from ..core.config import get_config
from .screens.agent_select import AgentSelectScreen
from .screens.chat_screen import ChatScreen


class DerekAgentApp(App):
    """Main TUI application."""

    TITLE = "Derek Agent Runner"
    SUB_TITLE = "Agno Framework TUI"
    CSS = """
    Screen {
        layout: vertical;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "退出", key_display="q"),
        Binding("ctrl+x", "quit", "退出", key_display="ctrl+x"),
        Binding("f10", "quit", "退出", key_display="f10"),
        Binding("a", "switch_agent", "切換 Agent", key_display="a"),
        Binding("n", "new_chat", "新對話", key_display="n"),
        Binding("h", "history", "歷史", key_display="h"),
        Binding("?", "help", "幫助", key_display="?"),
    ]

    def __init__(self):
        """Initialize the app."""
        super().__init__()
        self.runner: AgentRunner | None = None
        self._chat_screen: ChatScreen | None = None

    async def on_mount(self):
        """Called when app is mounted."""
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

        # Initialize runner
        try:
            self.runner = await get_runner()

            # Push chat screen
            self._chat_screen = ChatScreen(self.runner)
            await self.push_screen(self._chat_screen)

        except Exception as e:
            self.notify(f"初始化失敗: {e}", severity="error")
            self.exit(1)

    def action_switch_agent(self):
        """Switch to a different agent."""
        if self.runner:
            self.push_screen(AgentSelectScreen(self.runner), self._on_agent_selected)

    def _on_agent_selected(self, agent):
        """Handle agent selection."""
        if agent and self.runner:
            asyncio.create_task(self._switch_agent(agent.id))

    async def _switch_agent(self, agent_id: str):
        """Switch to the selected agent."""
        try:
            success = await self.runner.switch_agent(agent_id)
            if success and self._chat_screen:
                self._chat_screen.agent_name = self.runner.get_current_agent_name()
                self._chat_screen.add_message(
                    "system",
                    f"已切換至 Agent: {self._chat_screen.agent_name}",
                )
            else:
                self.notify("切換 Agent 失敗", severity="error")
        except Exception as e:
            self.notify(f"切換 Agent 出錯: {e}", severity="error")

    def action_new_chat(self):
        """Start a new conversation."""
        if self._chat_screen:
            self._chat_screen.action_new_chat()

    def action_history(self):
        """Show conversation history."""
        if self._chat_screen:
            self._chat_screen.action_history()

    def action_help(self):
        """Show help."""
        help_text = """
        # 快捷鍵說明

        - **q** / **ctrl+x** / **f10** - 退出程式
        - **a** - 切換 Agent
        - **n** - 開始新對話
        - **h** - 顯示對話歷史
        - **?** - 顯示此幫助
        - **Enter** - 發送訊息
        - **Shift+Enter** - 輸入多行文字

        # 關於

        Derek Agent Runner - 基於 Agno Framework 的 Agent 執行器
        """
        self.notify(help_text, title="幫助", timeout=10)

    async def on_unmount(self):
        """Called when app is unmounting."""
        if self.runner:
            await self.runner.shutdown()


def run_app():
    """Run the TUI application."""
    app = DerekAgentApp()
    app.run()
