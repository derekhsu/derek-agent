"""Python tool factory for Derek Agent Runner."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.config import AgentPythonConfig


def create_python_tool(
    python_config: "AgentPythonConfig",
    working_dir: str | None = None,
) -> "PythonTools | None":
    """Create a Python tool based on agent configuration.

    Args:
        python_config: Agent Python configuration.
        working_dir: Agent's working directory (fallback if python.base_dir not set).

    Returns:
        An Agno PythonTools instance, or None if Python is disabled.
    """
    if not python_config.enabled:
        return None

    # Determine base directory: python.base_dir > working_dir > temp dir
    if python_config.base_dir:
        base_dir = Path(python_config.base_dir)
    elif working_dir is not None:
        base_dir = Path(working_dir)
    else:
        # Default to temp directory for security isolation
        base_dir = Path(tempfile.gettempdir()) / "derek-agent-python"
        base_dir.mkdir(parents=True, exist_ok=True)

    # Build exclude list based on package installation setting
    exclude_tools: list[str] | None = None
    if not python_config.allow_package_installation:
        exclude_tools = ["pip_install_package", "uv_pip_install_package"]

    from agno.tools.python import PythonTools

    return PythonTools(
        base_dir=base_dir,
        restrict_to_base_dir=True,
        exclude_tools=exclude_tools,
    )
