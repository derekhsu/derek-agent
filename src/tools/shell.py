"""Shell tool factory for Derek Agent Runner."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.config import AgentShellConfig


def create_shell_tool(
    shell_config: "AgentShellConfig",
    working_dir: str | None = None,
) -> "ShellTools | None":
    """Create a shell tool based on agent configuration.

    Args:
        shell_config: Agent shell configuration.
        working_dir: Agent's working directory (fallback if shell.base_dir not set).

    Returns:
        An Agno ShellTools instance, or None if shell is disabled.
    """
    if not shell_config.enabled:
        return None

    # Use secure shell tools wrapper for command filtering and safety
    from .secure_shell_tools import create_secure_shell_tool
    return create_secure_shell_tool(shell_config, working_dir)
