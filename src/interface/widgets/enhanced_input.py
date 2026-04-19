"""Enhanced input with slash command support."""

from textual.message import Message
from textual.widgets import Input

from ..commands.registry import CommandRegistry, get_command_registry


class EnhancedInput(Input):
    """Input widget with slash command auto-completion.
    
    Emits SlashPrefixChanged when user types after '/'.
    Popup management is handled by the parent container (InputBar).
    """

    def __init__(
        self,
        registry: CommandRegistry | None = None,
        placeholder: str = "",
        id: str | None = None,
    ):
        """Initialize enhanced input.

        Args:
            registry: Command registry. If None, uses global registry.
            placeholder: Input placeholder.
            id: Widget ID.
        """
        super().__init__(placeholder=placeholder, id=id)
        self.registry = registry or get_command_registry()

    def is_slash_command(self) -> bool:
        """Check if current input is a slash command."""
        return self.value.startswith("/")

    def parse_slash_command(self) -> tuple[str, list[str]]:
        """Parse slash command into (name, args)."""
        if not self.is_slash_command():
            return "", []
        parts = self.value[1:].split()
        if not parts:
            return "", []
        return parts[0], parts[1:]

    def get_slash_prefix(self) -> str:
        """Get the prefix after '/' for autocomplete."""
        if not self.value.startswith("/"):
            return ""
        parts = self.value[1:].split(" ", 1)
        return parts[0]

    class SlashPrefixChanged(Message):
        """Emitted when input changes while in slash mode."""

        def __init__(self, prefix: str):
            self.prefix = prefix
            super().__init__()

    class SlashModeExited(Message):
        """Emitted when user leaves slash mode."""

        def __init__(self):
            super().__init__()
