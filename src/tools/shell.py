"""Shell tool factory for Derek Agent Runner."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.config import AgentShellConfig


def create_shell_tool(
    shell_config: "AgentShellConfig",
    working_dir: str | None = None,
) -> object | None:
    """Create a shell tool based on agent configuration.

    Args:
        shell_config: Agent shell configuration.
        working_dir: Agent's working directory (fallback if shell.base_dir not set).

    Returns:
        An Agno ShellTools instance, or None if shell is disabled.
    """
    if not shell_config.enabled:
        return None

    from agno.tools.shell import ShellTools

    # Determine base directory: shell.base_dir > working_dir > None (current dir)
    base_dir = None
    if shell_config.base_dir:
        base_dir = Path(shell_config.base_dir)
    elif working_dir:
        base_dir = Path(working_dir)

    return ShellTools(
        base_dir=base_dir,
        enable_run_shell_command=True,
    )
