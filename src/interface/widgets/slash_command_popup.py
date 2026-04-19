"""Slash command popup for auto-completion."""

from textual.containers import Vertical
from textual.message import Message
from textual.widgets import OptionList
from textual.widgets.option_list import Option

from ..commands.registry import CommandRegistry


class SlashCommandPopup(Vertical):
    """Popup for slash command auto-completion."""

    DEFAULT_CSS = """
    SlashCommandPopup {
        width: 100%;
        height: auto;
        max-height: 12;
        background: $surface;
        border: solid $primary;
    }

    SlashCommandPopup OptionList {
        width: 100%;
        height: auto;
        max-height: 10;
        border: none;
        background: $surface;
    }
    """

    def __init__(self, registry: CommandRegistry, prefix: str = ""):
        """Initialize slash command popup."""
        super().__init__()
        self.registry = registry
        self.prefix = prefix
        self._commands: list[str] = []

    def _build_options(self) -> list:
        """Build OptionList options from matching commands."""
        if self.prefix:
            commands = self.registry.find_matches(self.prefix)
        else:
            commands = self.registry.list_commands()

        self._commands = []
        options = []
        for cmd_class in commands:
            aliases_str = ", ".join([f"/{a}" for a in cmd_class.aliases[:2]])
            label = f"/{cmd_class.name}  {cmd_class.description}"
            if aliases_str:
                label += f"  ({aliases_str})"
            options.append(Option(label, id=cmd_class.name))
            self._commands.append(cmd_class.name)
        return options

    def compose(self):
        """Compose the popup."""
        options = self._build_options()
        if options:
            yield OptionList(*options, id="cmd-list")
        else:
            yield OptionList(Option("（無匹配指令）", disabled=True), id="cmd-list")

    def on_mount(self):
        """Called when popup is mounted."""
        opt = self.query_one("#cmd-list", OptionList)
        if self._commands:
            opt.highlighted = 0

    def update_commands(self):
        """Rebuild popup contents after prefix change."""
        options = self._build_options()
        opt = self.query_one("#cmd-list", OptionList)
        opt.clear_options()
        if options:
            for o in options:
                opt.add_option(o)
            opt.highlighted = 0
        else:
            opt.add_option(Option("（無匹配指令）", disabled=True))

    def select_next(self) -> None:
        """Highlight next item."""
        opt = self.query_one("#cmd-list", OptionList)
        count = len(self._commands)
        if count:
            current = opt.highlighted or 0
            opt.highlighted = (current + 1) % count

    def select_previous(self) -> None:
        """Highlight previous item."""
        opt = self.query_one("#cmd-list", OptionList)
        count = len(self._commands)
        if count:
            current = opt.highlighted or 0
            opt.highlighted = (current - 1) % count

    def get_selected_command(self) -> str | None:
        """Get currently highlighted command name."""
        opt = self.query_one("#cmd-list", OptionList)
        idx = opt.highlighted
        if idx is not None and 0 <= idx < len(self._commands):
            return self._commands[idx]
        return None

    def on_option_list_option_selected(self, event: OptionList.OptionSelected):
        """Handle click selection."""
        if event.option.id:
            self.post_message(self.CommandSelected(event.option.id))

    class CommandSelected(Message):
        """Emitted when a command is selected."""

        def __init__(self, command_name: str):
            self.command_name = command_name
            super().__init__()

    class Dismissed(Message):
        """Emitted when popup is dismissed."""

        def __init__(self):
            super().__init__()
