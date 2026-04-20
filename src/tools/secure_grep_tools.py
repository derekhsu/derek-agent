"""Secure grep tools wrapper using ripgrep with path traversal protection."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.config import AgentGrepConfig


class RipgrepError(Exception):
    """Error raised when ripgrep execution fails."""

    pass


class RipgrepTimeoutError(RipgrepError):
    """Error raised when ripgrep times out."""

    pass


class SecureGrepTools:
    """Secure wrapper for grep operations using ripgrep (rg)."""

    VCS_DIRECTORIES_TO_EXCLUDE = [".git", ".svn", ".hg", ".bzr", ".jj", ".sl"]

    def __init__(
        self,
        base_dir: Path | None = None,
        max_results: int = 250,
        timeout_seconds: int = 20,
    ):
        """Initialize secure grep tools.

        Args:
            base_dir: The base directory that searches are allowed to access.
                     If None, uses current working directory.
            max_results: Default maximum number of results (head_limit).
            timeout_seconds: Timeout for ripgrep execution in seconds.
        """
        self.base_dir = base_dir
        self.max_results = max_results
        self.timeout_seconds = timeout_seconds
        self._rg_path: str | None = None

    def _find_rg(self) -> str:
        """Find ripgrep executable path."""
        if self._rg_path is not None:
            return self._rg_path

        # Try to find rg in PATH
        for name in ("rg", "ripgrep"):
            try:
                result = subprocess.run(
                    ["which", name],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0 and result.stdout.strip():
                    self._rg_path = result.stdout.strip()
                    return self._rg_path
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        # Fallback to 'rg' and let it resolve via PATH
        self._rg_path = "rg"
        return self._rg_path

    def _validate_path(self, file_path: str) -> Path:
        """Validate that a file path is within the allowed base directory."""
        if self.base_dir is None:
            base_dir = Path.cwd()
        else:
            base_dir = self.base_dir

        resolved_path = Path(file_path).resolve()
        resolved_base = base_dir.resolve()

        try:
            resolved_path.relative_to(resolved_base)
            return resolved_path
        except ValueError:
            raise ValueError(
                f"Path '{file_path}' (resolved to '{resolved_path}') "
                f"is outside the allowed base directory '{resolved_base}'"
            )

    def _build_args(
        self,
        pattern: str,
        path: str,
        glob: str | None,
        output_mode: str,
        context_before: int | None,
        context_after: int | None,
        context: int | None,
        show_line_numbers: bool,
        case_insensitive: bool,
        file_type: str | None,
        head_limit: int | None,
        offset: int,
        multiline: bool,
    ) -> tuple[list[str], Path]:
        """Build ripgrep command arguments."""
        validated_path = self._validate_path(path)
        args = ["--hidden"]

        # Exclude VCS directories
        for dir in self.VCS_DIRECTORIES_TO_EXCLUDE:
            args.extend(["--glob", f"!{dir}"])

        # Limit line length to prevent base64/minified content from cluttering output
        args.extend(["--max-columns", "500"])

        # Multiline mode
        if multiline:
            args.extend(["-U", "--multiline-dotall"])

        # Case insensitive
        if case_insensitive:
            args.append("-i")

        # Output mode
        if output_mode == "files_with_matches":
            args.append("-l")
        elif output_mode == "count":
            args.append("-c")

        # Line numbers for content mode
        if show_line_numbers and output_mode == "content":
            args.append("-n")

        # Context flags
        if output_mode == "content":
            if context is not None:
                args.extend(["-C", str(context)])
            else:
                if context_before is not None:
                    args.extend(["-B", str(context_before)])
                if context_after is not None:
                    args.extend(["-A", str(context_after)])

        # Pattern (use -e if starts with dash)
        if pattern.startswith("-"):
            args.extend(["-e", pattern])
        else:
            args.append(pattern)

        # File type
        if file_type:
            args.extend(["--type", file_type])

        # Glob patterns
        if glob:
            # Split on commas and spaces
            for raw_pattern in glob.split():
                if "{" in raw_pattern and "}" in raw_pattern:
                    # Pattern contains braces, don't split further
                    args.extend(["--glob", raw_pattern])
                else:
                    # Split on commas
                    for p in raw_pattern.split(","):
                        if p:
                            args.extend(["--glob", p])

        return args, validated_path

    def _apply_head_limit(
        self,
        items: list[str],
        limit: int | None,
        offset: int,
    ) -> tuple[list[str], int | None]:
        """Apply head_limit and offset to results."""
        if limit == 0:
            return items[offset:], None
        effective_limit = limit if limit is not None else self.max_results
        sliced = items[offset : offset + effective_limit]
        was_truncated = len(items) - offset > effective_limit
        return sliced, effective_limit if was_truncated else None

    def grep(
        self,
        pattern: str,
        path: str = ".",
        glob: str | None = None,
        output_mode: str = "files_with_matches",
        context_before: int | None = None,
        context_after: int | None = None,
        context: int | None = None,
        show_line_numbers: bool = True,
        case_insensitive: bool = False,
        file_type: str | None = None,
        head_limit: int | None = None,
        offset: int = 0,
        multiline: bool = False,
    ) -> dict[str, Any]:
        """Search for pattern in files using ripgrep.

        Args:
            pattern: Regular expression pattern to search for.
            path: Directory or file to search in (default: current directory).
            glob: Glob pattern to filter files (e.g., "*.py", "*.{ts,tsx}").
            output_mode: Output mode - "content", "files_with_matches", or "count".
            context_before: Number of lines to show before each match.
            context_after: Number of lines to show after each match.
            context: Number of lines to show before and after each match.
            show_line_numbers: Show line numbers in content mode.
            case_insensitive: Case insensitive search.
            file_type: File type filter (e.g., "py", "js", "rust").
            head_limit: Maximum number of results (0 for unlimited).
            offset: Skip first N results.
            multiline: Enable multiline mode.

        Returns:
            Dictionary with search results:
            - mode: output mode used
            - numFiles: number of files (for files_with_matches)
            - filenames: list of matching file paths
            - content: search results content (for content mode)
            - numLines: number of lines (for content mode)
            - numMatches: total matches (for count mode)
            - appliedLimit: limit that was applied (if any)
            - appliedOffset: offset that was applied
        """
        args, validated_path = self._build_args(
            pattern=pattern,
            path=path,
            glob=glob,
            output_mode=output_mode,
            context_before=context_before,
            context_after=context_after,
            context=context,
            show_line_numbers=show_line_numbers,
            case_insensitive=case_insensitive,
            file_type=file_type,
            head_limit=head_limit,
            offset=offset,
            multiline=multiline,
        )

        rg_path = self._find_rg()

        try:
            result = subprocess.run(
                [rg_path] + args + [str(validated_path)],
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            raise RipgrepTimeoutError(
                f"Ripgrep search timed out after {self.timeout_seconds} seconds."
            )

        # Exit code 0 = matches found, 1 = no matches (both are success)
        if result.returncode not in (0, 1):
            stderr = result.stderr.strip()
            if "matched" in stderr.lower() or result.returncode == 1:
                pass  # No matches is not an error
            else:
                raise RipgrepError(f"Ripgrep failed: {stderr or 'unknown error'}")

        lines = [line for line in result.stdout.strip().split("\n") if line]

        # Process results based on output mode
        if output_mode == "content":
            limited_lines, applied_limit = self._apply_head_limit(lines, head_limit, offset)

            # Convert absolute paths to relative paths
            final_lines = []
            cwd = Path.cwd()
            for line in limited_lines:
                colon_idx = line.index(":") if ":" in line else -1
                if colon_idx > 0:
                    file_path = line[:colon_idx]
                    rest = line[colon_idx:]
                    try:
                        rel_path = Path(file_path).relative_to(cwd)
                        final_lines.append(str(rel_path) + rest)
                    except ValueError:
                        final_lines.append(line)
                else:
                    final_lines.append(line)

            return {
                "mode": "content",
                "numFiles": 0,
                "filenames": [],
                "content": "\n".join(final_lines),
                "numLines": len(final_lines),
                "appliedLimit": applied_limit,
                "appliedOffset": offset if offset > 0 else None,
            }

        if output_mode == "count":
            limited_lines, applied_limit = self._apply_head_limit(lines, head_limit, offset)

            # Convert paths to relative
            cwd = Path.cwd()
            final_lines = []
            total_matches = 0
            file_count = 0
            for line in limited_lines:
                colon_idx = line.rfind(":")
                if colon_idx > 0:
                    file_path = line[:colon_idx]
                    count_str = line[colon_idx + 1 :]
                    try:
                        rel_path = Path(file_path).relative_to(cwd)
                        final_lines.append(str(rel_path) + ":" + count_str)
                    except ValueError:
                        final_lines.append(line)
                    try:
                        count = int(count_str)
                        total_matches += count
                        file_count += 1
                    except ValueError:
                        pass
                else:
                    final_lines.append(line)

            return {
                "mode": "count",
                "numFiles": file_count,
                "filenames": [],
                "content": "\n".join(final_lines),
                "numMatches": total_matches,
                "appliedLimit": applied_limit,
                "appliedOffset": offset if offset > 0 else None,
            }

        # files_with_matches mode (default)
        # Sort by modification time (most recent first)
        def get_mtime(p: str) -> float:
            try:
                return os.path.getmtime(p)
            except OSError:
                return 0

        sorted_lines = sorted(lines, key=get_mtime, reverse=True)
        limited_lines, applied_limit = self._apply_head_limit(sorted_lines, head_limit, offset)

        # Convert to relative paths
        cwd = Path.cwd()
        relative_files = []
        for file_path in limited_lines:
            try:
                rel_path = Path(file_path).relative_to(cwd)
                relative_files.append(str(rel_path))
            except ValueError:
                relative_files.append(file_path)

        return {
            "mode": "files_with_matches",
            "numFiles": len(relative_files),
            "filenames": relative_files,
            "appliedLimit": applied_limit,
            "appliedOffset": offset if offset > 0 else None,
        }

    def get_available_tools(self) -> list[dict[str, Any]]:
        """Get available tools for Agno integration.

        Returns a list of tool definitions compatible with Agno's tool system.
        """
        return [
            {
                "name": "grep",
                "description": "Search for patterns in file contents using ripgrep (rg). Supports regex, file type filtering, context lines, and multiple output modes.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "The regular expression pattern to search for in file contents",
                        },
                        "path": {
                            "type": "string",
                            "description": "File or directory to search in. Defaults to current working directory.",
                        },
                        "glob": {
                            "type": "string",
                            "description": "Glob pattern to filter files (e.g., '*.py', '*.{ts,tsx}')",
                        },
                        "output_mode": {
                            "type": "string",
                            "enum": ["content", "files_with_matches", "count"],
                            "description": "Output mode: 'content' shows matching lines with context, 'files_with_matches' shows file paths, 'count' shows match counts per file",
                            "default": "files_with_matches",
                        },
                        "context_before": {
                            "type": "integer",
                            "description": "Number of lines to show before each match (like grep -B)",
                        },
                        "context_after": {
                            "type": "integer",
                            "description": "Number of lines to show after each match (like grep -A)",
                        },
                        "context": {
                            "type": "integer",
                            "description": "Number of lines to show before and after each match (like grep -C)",
                        },
                        "show_line_numbers": {
                            "type": "boolean",
                            "description": "Show line numbers in output (for content mode)",
                            "default": True,
                        },
                        "case_insensitive": {
                            "type": "boolean",
                            "description": "Case insensitive search (like grep -i)",
                            "default": False,
                        },
                        "file_type": {
                            "type": "string",
                            "description": "File type to search (e.g., 'py', 'js', 'rust'). More efficient than glob for standard types.",
                        },
                        "head_limit": {
                            "type": "integer",
                            "description": "Limit output to first N results. 0 for unlimited. Defaults to 250.",
                        },
                        "offset": {
                            "type": "integer",
                            "description": "Skip first N results before applying head_limit",
                            "default": 0,
                        },
                        "multiline": {
                            "type": "boolean",
                            "description": "Enable multiline mode where . matches newlines",
                            "default": False,
                        },
                    },
                    "required": ["pattern"],
                },
            }
        ]


def create_secure_grep_tool(
    grep_config: "AgentGrepConfig",
    working_dir: str | None = None,
) -> SecureGrepTools | None:
    """Create a secure grep tool based on agent configuration.

    Args:
        grep_config: Agent grep configuration.
        working_dir: Agent's working directory (fallback if grep.base_dir not set).

    Returns:
        A SecureGrepTools instance, or None if grep is disabled.
    """
    if not grep_config.enabled:
        return None

    base_dir = None
    if grep_config.base_dir:
        base_dir = Path(grep_config.base_dir)
    elif working_dir is not None:
        base_dir = Path(working_dir)

    return SecureGrepTools(
        base_dir=base_dir,
        max_results=grep_config.max_results,
        timeout_seconds=grep_config.timeout_seconds,
    )
