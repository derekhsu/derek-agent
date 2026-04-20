"""History screen for Derek Agent Runner TUI."""

from datetime import datetime

from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, ListItem, ListView, Static

from ...core.agent_runner import AgentRunner
from ...storage import Session


def format_relative_time(dt: datetime) -> str:
    """Format datetime as relative time string."""
    now = datetime.now()
    diff = now - dt

    seconds = diff.total_seconds()

    if seconds < 60:
        return "剛剛"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} 分鐘前"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} 小時前"
    else:
        days = int(seconds / 86400)
        return f"{days} 天前"


class HistoryScreen(ModalScreen):
    """Conversation history selection modal screen."""

    DEFAULT_CSS = """
    HistoryScreen {
        align: center middle;
    }

    HistoryScreen > Vertical {
        width: 70;
        height: auto;
        max-height: 30;
        border: thick $background 80%;
        padding: 1 2;
        background: $surface;
    }

    HistoryScreen #title {
        text-align: center;
        text-style: bold;
        height: 3;
        content-align: center middle;
    }

    HistoryScreen #search-container {
        height: auto;
        margin-bottom: 1;
    }

    HistoryScreen #search-input {
        width: 100%;
    }

    HistoryScreen ListView {
        width: 100%;
        height: 1fr;
        min-height: 5;
        border: solid $primary;
    }

    HistoryScreen ListItem {
        padding: 0 1;
        height: auto;
    }

    HistoryScreen ListItem Vertical {
        height: auto;
        width: 100%;
    }

    HistoryScreen ListItem Label {
        height: auto;
        padding: 0;
    }

    HistoryScreen ListItem:hover {
        background: $primary-darken-2;
    }

    HistoryScreen ListItem:focus {
        background: $primary-darken-1;
    }

    HistoryScreen .session-title {
        text-style: bold;
    }

    HistoryScreen .session-meta {
        color: $text-muted;
        text-style: dim;
    }

    HistoryScreen #buttons {
        height: auto;
        margin-top: 1;
    }

    HistoryScreen #buttons Button {
        margin-right: 1;
    }

    HistoryScreen .empty-state {
        text-align: center;
        color: $text-muted;
        text-style: dim;
        padding: 1;
        height: auto;
    }
    """

    def __init__(self, runner: AgentRunner, agent_name: str):
        """Initialize history screen.

        Args:
            runner: Agent runner instance.
            agent_name: Current agent name for display.
        """
        super().__init__()
        self.runner = runner
        self.agent_name = agent_name
        self._sessions: list[Session] = []
        self._filtered_sessions: list[Session] = []

    def compose(self):
        """Compose the screen."""
        with Vertical():
            yield Static(f"對話歷史 - {self.agent_name}", id="title")

            with Horizontal(id="search-container"):
                yield Input(placeholder="搜尋對話標題...", id="search-input")

            list_view = ListView(id="session-list")
            list_view.can_focus = True
            yield list_view

            with Horizontal(id="buttons"):
                yield Button("載入 (Enter)", id="load-btn", variant="primary")
                yield Button("刪除 (d)", id="delete-btn", variant="error")
                yield Button("取消 (Esc)", id="cancel-btn", variant="default")

    async def on_mount(self):
        """Called when screen is mounted."""
        await self._load_sessions()
        self.query_one("#search-input", Input).focus()

    async def _load_sessions(self):
        """Load sessions from storage."""
        try:
            self._sessions = await self.runner.list_conversations(limit=100)
            # Sort by updated_at descending (newest first)
            self._sessions.sort(key=lambda s: s.updated_at, reverse=True)
            self._filtered_sessions = self._sessions.copy()
            self._update_list()
        except Exception as e:
            self.notify(f"載入對話歷史失敗: {e}", severity="error")

    def _update_list(self):
        """Update the list view with current sessions."""
        list_view = self.query_one("#session-list", ListView)
        list_view.clear()

        if not self._filtered_sessions:
            # Show empty state
            list_view.mount(
                Static(
                    "沒有對話記錄" if not self._sessions else "沒有符合的對話",
                    classes="empty-state",
                )
            )
            return

        for session in self._filtered_sessions:
            # Build display info
            title = session.title or "未命名對話"
            time_str = format_relative_time(session.updated_at)
            msg_count = len(session.messages)

            # Get metrics summary
            total_metrics = session.get_total_metrics()
            token_str = f"{total_metrics.total_tokens:,} tokens" if total_metrics.total_tokens > 0 else ""

            meta_parts = [time_str, f"{msg_count} 則訊息"]
            if token_str:
                meta_parts.append(token_str)
            meta_text = " | ".join(meta_parts)

            item = ListItem(
                Vertical(
                    Label(title, classes="session-title"),
                    Label(meta_text, classes="session-meta"),
                ),
            )
            list_view.append(item)

    def _filter_sessions(self, query: str):
        """Filter sessions by search query."""
        if not query.strip():
            self._filtered_sessions = self._sessions.copy()
        else:
            query_lower = query.lower()
            self._filtered_sessions = [
                s for s in self._sessions if query_lower in (s.title or "").lower()
            ]
        self._update_list()

    def on_input_changed(self, event: Input.Changed):
        """Handle search input changes."""
        if event.input.id == "search-input":
            self._filter_sessions(event.value)

    def on_list_view_selected(self, event: ListView.Selected):
        """Handle session selection."""
        # Get selected index and lookup session from filtered list
        list_view = self.query_one("#session-list", ListView)
        selected = list_view.index
        if selected is not None and 0 <= selected < len(self._filtered_sessions):
            session = self._filtered_sessions[selected]
            self.dismiss(session)

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button press."""
        if event.button.id == "load-btn":
            self._load_selected()
        elif event.button.id == "delete-btn":
            self._delete_selected()
        elif event.button.id == "cancel-btn":
            self.dismiss(None)

    def _load_selected(self):
        """Load the selected session."""
        list_view = self.query_one("#session-list", ListView)
        selected = list_view.index

        if selected is not None and 0 <= selected < len(self._filtered_sessions):
            session = self._filtered_sessions[selected]
            self.dismiss(session)
            return

        self.notify("請先選擇一個對話", severity="warning")

    async def _delete_selected(self):
        """Delete the selected session."""
        list_view = self.query_one("#session-list", ListView)
        selected = list_view.index

        if selected is None or not (0 <= selected < len(self._filtered_sessions)):
            self.notify("請先選擇一個對話", severity="warning")
            return

        session = self._filtered_sessions[selected]

        # Show confirmation with session title
        title = session.title or "未命名對話"

        def on_confirm(confirmed: bool):
            if confirmed:
                self.run_worker(self._do_delete(session))

        self.app.push_screen(
            ConfirmScreen(
                f'確定要刪除對話 "{title}" 嗎？\n此操作無法復原。',
                on_confirm,
            )
        )

    async def _do_delete(self, session: Session):
        """Perform the actual deletion."""
        try:
            success = await self.runner.conversation_manager.delete_session(session.id)
            if success:
                self.notify("對話已刪除", severity="information")
                # Reload list
                await self._load_sessions()
            else:
                self.notify("刪除失敗", severity="error")
        except Exception as e:
            self.notify(f"刪除失敗: {e}", severity="error")

    def on_key(self, event):
        """Handle key press."""
        if event.key == "escape":
            self.dismiss(None)
        elif event.key == "l" or event.key == "enter":
            focused = self.app.focused
            if not isinstance(focused, Input):
                self._load_selected()
        elif event.key == "d":
            focused = self.app.focused
            if not isinstance(focused, Input):
                self.run_worker(self._delete_selected())
        elif event.key == "slash" or event.key == "s":
            self.query_one("#search-input", Input).focus()


class ConfirmScreen(ModalScreen):
    """Simple confirmation dialog."""

    DEFAULT_CSS = """
    ConfirmScreen {
        align: center middle;
    }

    ConfirmScreen > Vertical {
        width: 60;
        height: auto;
        max-height: 20;
        border: thick $background 80%;
        padding: 1 2;
        background: $surface;
    }

    ConfirmScreen #message {
        height: auto;
        padding: 1;
        content-align: center middle;
    }

    ConfirmScreen #buttons {
        height: auto;
        margin-top: 1;
        align: center middle;
    }

    ConfirmScreen Button {
        margin: 0 1;
    }
    """

    def __init__(self, message: str, callback):
        """Initialize confirm screen.

        Args:
            message: Message to display.
            callback: Function to call with True/False result.
        """
        super().__init__()
        self.message = message
        self.callback = callback

    def compose(self):
        """Compose the screen."""
        with Vertical():
            yield Static(self.message, id="message")
            with Horizontal(id="buttons"):
                yield Button("確定", id="confirm-btn", variant="error")
                yield Button("取消", id="cancel-btn", variant="default")

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button press."""
        if event.button.id == "confirm-btn":
            self.callback(True)
        else:
            self.callback(False)
        self.dismiss()

    def on_key(self, event):
        """Handle key press."""
        if event.key == "escape":
            self.callback(False)
            self.dismiss()
        elif event.key == "enter":
            self.callback(True)
            self.dismiss()
