"""File tool factory for Derek Agent Runner."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.config import AgentFileConfig


def validate_file_path(base_dir: Path | None, file_path: str) -> Path:
    """Validate that a file path is within the allowed base directory.
    
    Args:
        base_dir: The base directory that files are allowed to access.
        file_path: The file path to validate.
        
    Returns:
        The resolved absolute path if it's safe.
        
    Raises:
        ValueError: If the path attempts to traverse outside the base directory.
    """
    if base_dir is None:
        # If no base directory is set, resolve relative to current working directory
        base_dir = Path.cwd()
    
    # Resolve the file path to an absolute path
    resolved_path = Path(file_path).resolve()
    
    # Resolve the base directory to an absolute path
    resolved_base = base_dir.resolve()
    
    # Check if the resolved path is within the base directory
    try:
        resolved_path.relative_to(resolved_base)
        return resolved_path
    except ValueError:
        raise ValueError(
            f"Path '{file_path}' (resolved to '{resolved_path}') "
            f"is outside the allowed base directory '{resolved_base}'"
        )


def create_file_tool(
    file_config: "AgentFileConfig",
    working_dir: str | None = None,
) -> "FileTools | None":
    """Create a file tool based on agent configuration.

    Args:
        file_config: Agent file configuration.
        working_dir: Agent's working directory (fallback if file.base_dir not set).

    Returns:
        An Agno FileTools instance, or None if file is disabled.
    """
    if not file_config.enabled:
        return None

    # Use secure file tools wrapper for path traversal protection
    from .secure_file_tools import create_secure_file_tool
    return create_secure_file_tool(file_config, working_dir)
