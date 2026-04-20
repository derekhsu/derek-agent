"""Secure file tools wrapper with path traversal protection."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.config import AgentFileConfig


class SecureFileTools:
    """Secure wrapper for file operations with path traversal protection."""

    def __init__(self, base_dir: Path | None = None):
        """Initialize secure file tools.
        
        Args:
            base_dir: The base directory that files are allowed to access.
                     If None, uses current working directory.
        """
        self.base_dir = base_dir
        self._file_tools = None
        self._init_file_tools()

    def _init_file_tools(self) -> None:
        """Initialize the underlying Agno FileTools."""
        try:
            from agno.tools.file import FileTools
            self._file_tools = FileTools(
                base_dir=self.base_dir,
                enable_save_file=True,
                enable_read_file=True,
                enable_delete_file=False,  # Keep delete disabled for safety
                enable_list_files=True,
                enable_search_files=True,
                enable_read_file_chunk=True,
                enable_replace_file_chunk=True,
                enable_search_content=True,
            )
        except ImportError:
            self._file_tools = None

    def _validate_path(self, file_path: str) -> Path:
        """Validate that a file path is within the allowed base directory."""
        if self.base_dir is None:
            # If no base directory is set, resolve relative to current working directory
            base_dir = Path.cwd()
        else:
            base_dir = self.base_dir
        
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

    def read_file(self, file_path: str) -> str:
        """Read file content with path validation."""
        validated_path = self._validate_path(file_path)
        if self._file_tools:
            return self._file_tools.read_file(str(validated_path))
        else:
            with open(validated_path, 'r', encoding='utf-8') as f:
                return f.read()

    def save_file(self, file_path: str, content: str) -> str:
        """Save file content with path validation."""
        validated_path = self._validate_path(file_path)
        if self._file_tools:
            return self._file_tools.save_file(str(validated_path), content)
        else:
            # Create parent directories if they don't exist
            validated_path.parent.mkdir(parents=True, exist_ok=True)
            with open(validated_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"File saved to {validated_path}"

    def list_files(self, directory: str = ".") -> list[str]:
        """List files in directory with path validation."""
        validated_path = self._validate_path(directory)
        if self._file_tools:
            return self._file_tools.list_files(str(validated_path))
        else:
            if not validated_path.exists() or not validated_path.is_dir():
                return []
            return [str(p.relative_to(validated_path)) for p in validated_path.iterdir()]

    def search_files(self, pattern: str, directory: str = ".") -> list[str]:
        """Search for files with pattern and path validation."""
        validated_path = self._validate_path(directory)
        if self._file_tools:
            return self._file_tools.search_files(pattern, str(validated_path))
        else:
            import glob
            search_path = validated_path / pattern
            return [str(p.relative_to(validated_path)) for p in glob.glob(str(search_path))]

    def get_available_tools(self) -> list[dict[str, Any]]:
        """Get available tools for Agno integration."""
        if self._file_tools:
            return self._file_tools.get_available_tools()
        return []


def create_secure_file_tool(
    file_config: "AgentFileConfig",
    working_dir: str | None = None,
) -> SecureFileTools | None:
    """Create a secure file tool based on agent configuration.

    Args:
        file_config: Agent file configuration.
        working_dir: Agent's working directory (fallback if file.base_dir not set).

    Returns:
        A SecureFileTools instance, or None if file is disabled.
    """
    if not file_config.enabled:
        return None

    # Determine base directory: file.base_dir > working_dir > current dir
    base_dir = None
    if file_config.base_dir:
        base_dir = Path(file_config.base_dir)
    elif working_dir is not None:
        base_dir = Path(working_dir)

    return SecureFileTools(base_dir=base_dir)
