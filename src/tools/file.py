"""File tool factory for Derek Agent Runner."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.config import AgentFileConfig


def create_file_tool(
    file_config: "AgentFileConfig",
    working_dir: str | None = None,
) -> object | None:
    """Create a file tool based on agent configuration.

    Args:
        file_config: Agent file configuration.
        working_dir: Agent's working directory (fallback if file.base_dir not set).

    Returns:
        An Agno FileTools instance, or None if file is disabled.
    """
    if not file_config.enabled:
        return None

    from agno.tools.file import FileTools

    # Determine base directory: file.base_dir > working_dir > None (current dir)
    base_dir = None
    if file_config.base_dir:
        base_dir = Path(file_config.base_dir)
    elif working_dir:
        base_dir = Path(working_dir)

    return FileTools(
        base_dir=base_dir,
        enable_save_file=True,
        enable_read_file=True,
        enable_delete_file=False,  # Delete disabled by default for safety
        enable_list_files=True,
        enable_search_files=True,
        enable_read_file_chunk=True,
        enable_replace_file_chunk=True,
        enable_search_content=True,
    )
