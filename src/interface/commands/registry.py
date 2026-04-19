"""Command registry for slash commands."""

from typing import Any, Type

from .base import Command, CommandResult


class CommandRegistry:
    """Registry for managing slash commands."""

    def __init__(self):
        """Initialize command registry."""
        self._commands: dict[str, Type[Command]] = {}
        self._aliases: dict[str, str] = {}

    def register(self, command_class: Type[Command]) -> None:
        """Register a command class.

        Args:
            command_class: The command class to register.
        """
        name = command_class.name
        self._commands[name] = command_class

        # Register aliases
        for alias in command_class.aliases:
            self._aliases[alias] = name

    def unregister(self, name: str) -> bool:
        """Unregister a command.

        Args:
            name: Command name.

        Returns:
            True if command was found and removed.
        """
        if name in self._commands:
            del self._commands[name]
            # Remove aliases pointing to this command
            self._aliases = {k: v for k, v in self._aliases.items() if v != name}
            return True
        return False

    def get(self, name: str) -> Type[Command] | None:
        """Get command class by name or alias.

        Args:
            name: Command name or alias.

        Returns:
            Command class or None.
        """
        # Check if it's an alias
        if name in self._aliases:
            name = self._aliases[name]
        return self._commands.get(name)

    def list_commands(self) -> list[Type[Command]]:
        """List all registered commands.

        Returns:
            List of command classes.
        """
        return list(self._commands.values())

    def find_matches(self, prefix: str) -> list[Type[Command]]:
        """Find commands matching prefix.

        Args:
            prefix: Command name prefix (without the leading /).

        Returns:
            List of matching command classes.
        """
        matches = []
        for name, cmd_class in self._commands.items():
            if name.startswith(prefix):
                matches.append(cmd_class)
        return matches

    async def execute(
        self, name: str, args: list[str], app: Any = None, runner: Any = None
    ) -> CommandResult:
        """Execute a command.

        Args:
            name: Command name.
            args: Command arguments.
            app: The TUI app instance.
            runner: The agent runner instance.

        Returns:
            Command result.
        """
        cmd_class = self.get(name)
        if not cmd_class:
            return CommandResult(
                success=False, message=f"未知指令: /{name}"
            )

        try:
            cmd = cmd_class(app=app, runner=runner)
            # Validate args
            is_valid, error = cmd.validate_args(args)
            if not is_valid:
                return CommandResult(success=False, message=error)

            # Execute
            message = await cmd.execute(args)
            return CommandResult(success=True, message=message)
        except Exception as e:
            return CommandResult(success=False, message=f"指令執行失敗: {e}")

    def get_all_names(self) -> list[str]:
        """Get all command names including aliases.

        Returns:
            List of all names.
        """
        names = list(self._commands.keys())
        names.extend(self._aliases.keys())
        return sorted(set(names))


# Global registry instance
_registry: CommandRegistry | None = None


def get_command_registry() -> CommandRegistry:
    """Get global command registry."""
    global _registry
    if _registry is None:
        _registry = CommandRegistry()
    return _registry


def reset_command_registry() -> None:
    """Reset global command registry."""
    global _registry
    _registry = None
