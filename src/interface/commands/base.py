"""Base classes for slash commands."""

from abc import ABC, abstractmethod
from typing import Any


class Command(ABC):
    """Base class for slash commands."""

    name: str = ""
    description: str = ""
    usage: str = ""
    aliases: list[str] = []

    def __init__(self, app: Any = None, runner: Any = None):
        """Initialize command.

        Args:
            app: The TUI app instance.
            runner: The agent runner instance.
        """
        self.app = app
        self.runner = runner

    @abstractmethod
    async def execute(self, args: list[str]) -> str:
        """Execute the command.

        Args:
            args: Command arguments.

        Returns:
            Result message to display.
        """
        pass

    def get_completions(self, partial: str) -> list[str]:
        """Get completion suggestions for arguments.

        Args:
            partial: Partial argument text.

        Returns:
            List of completion suggestions.
        """
        return []

    def validate_args(self, args: list[str]) -> tuple[bool, str]:
        """Validate command arguments.

        Args:
            args: Command arguments.

        Returns:
            Tuple of (is_valid, error_message).
        """
        return True, ""


class CommandResult:
    """Result of a command execution."""

    def __init__(
        self,
        success: bool,
        message: str = "",
        should_exit: bool = False,
        refresh_ui: bool = False,
    ):
        self.success = success
        self.message = message
        self.should_exit = should_exit
        self.refresh_ui = refresh_ui
