"""Agent selection screen for Derek Agent Runner TUI."""

from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Label, ListItem, ListView, Static

from ...core.agent_runner import AgentRunner
from ...core.config import AgentConfig


class AgentSelectScreen(ModalScreen):
    """Agent selection modal screen."""

    DEFAULT_CSS = """
    AgentSelectScreen {
        align: center middle;
    }

    AgentSelectScreen > Vertical {
        width: 60;
        height: auto;
        max-height: 30;
        border: thick $background 80%;
        padding: 1 2;
        background: $surface;
    }

    AgentSelectScreen #title {
        text-align: center;
        text-style: bold;
        height: 3;
        content-align: center middle;
    }

    AgentSelectScreen ListView {
        width: 100%;
        height: auto;
        max-height: 20;
        border: solid $primary;
    }

    AgentSelectScreen ListItem {
        padding: 1;
    }

    AgentSelectScreen ListItem:hover {
        background: $primary-darken-2;
    }

    AgentSelectScreen ListItem:focus {
        background: $primary-darken-1;
    }

    AgentSelectScreen .agent-name {
        text-style: bold;
    }

    AgentSelectScreen .agent-desc {
        color: $text-muted;
        text-style: dim;
    }

    AgentSelectScreen #buttons {
        height: auto;
        margin-top: 1;
    }
    """

    def __init__(self, runner: AgentRunner):
        """Initialize agent select screen.

        Args:
            runner: Agent runner instance.
        """
        super().__init__()
        self.runner = runner
        self._agents: list[AgentConfig] = []

    def compose(self):
        """Compose the screen."""
        with Vertical():
            yield Static("選擇 Agent", id="title")

            list_view = ListView(id="agent-list")
            list_view.can_focus = True
            yield list_view

            with Vertical(id="buttons"):
                yield Button("取消", id="cancel-btn", variant="default")

    def on_mount(self):
        """Called when screen is mounted."""
        self._load_agents()

    def _load_agents(self):
        """Load agents into the list."""
        self._agents = self.runner.list_available_agents()
        list_view = self.query_one("#agent-list", ListView)

        for agent in self._agents:
            desc = agent.description or agent.system_prompt[:50] + "..."
            item = ListItem(
                Vertical(
                    Label(agent.name, classes="agent-name"),
                    Label(desc, classes="agent-desc"),
                    Label(f"模型: {agent.model}", classes="agent-desc"),
                ),
                data=agent,
            )
            list_view.append(item)

    def on_list_view_selected(self, event: ListView.Selected):
        """Handle agent selection."""
        agent = event.item.data
        if agent:
            self.dismiss(agent)

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button press."""
        if event.button.id == "cancel-btn":
            self.dismiss(None)

    def on_key(self, event):
        """Handle key press."""
        if event.key == "escape":
            self.dismiss(None)
