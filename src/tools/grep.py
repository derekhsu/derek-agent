"""Grep tool using ripgrep, integrated as an Agno Toolkit."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any

from agno.tools.toolkit import Toolkit


class GrepTools(Toolkit):
    """Grep tool using ripgrep (rg) for fast content search.

    Inherits from Agno Toolkit to properly integrate with the Agent tool system.
    """

    VCS_DIRECTORIES_TO_EXCLUDE = [".git", ".svn", ".hg", ".bzr", ".jj", ".sl"]
    DEFAULT_MAX_RESULTS = 250
    DEFAULT_TIMEOUT = 20

    def __init__(
        self,
        base_dir: str | Path | None = None,
        max_results: int = DEFAULT_MAX_RESULTS,
        timeout_seconds: int = DEFAULT_TIMEOUT,
        **kwargs: Any,
    ):
        """Initialize GrepTools.

        Args:
            base_dir: Base directory for searches. Defaults to cwd.
            max_results: Default maximum number of results.
            timeout_seconds: Timeout for ripgrep execution.
            **kwargs: Passed to Toolkit base class.
        """
        self._base_dir = Path(base_dir) if base_dir else None
        self.max_results = max_results
        self.timeout_seconds = timeout_seconds

        # Initialize the Toolkit with no tools - we'll register manually
        kwargs.setdefault("name", "grep")
        kwargs.setdefault("auto_register", False)
        super().__init__(**kwargs)

        # Register the grep tool
        from agno.tools.function import Function

        self.register(
            Function(
                name="grep",
                description="Search for patterns in file contents using ripgrep (rg). Supports regex, file type filtering, context lines, and multiple output modes. Use this when you need to find code, text, or patterns within files.",
                entrypoint=self.grep,
                parameters={
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
                        },
                        "case_insensitive": {
                            "type": "boolean",
                            "description": "Case insensitive search (like grep -i)",
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
                        },
                        "multiline": {
                            "type": "boolean",
                            "description": "Enable multiline mode where . matches newlines",
                        },
                    },
                    "required": ["pattern"],
                },
            )
        )

    def _find_rg(self) -> str:
        """Find ripgrep executable path."""
        for name in ("rg", "ripgrep"):
            try:
                result = subprocess.run(
                    ["which", name],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
        return "rg"

    def _validate_path(self, file_path: str) -> Path:
        """Validate that a path is within the allowed base directory."""
        base = self._base_dir.resolve() if self._base_dir else Path.cwd()
        resolved = Path(file_path).resolve()
        try:
            resolved.relative_to(base)
            return resolved
        except ValueError:
            raise ValueError(
                f"Path '{file_path}' is outside the allowed base directory '{base}'"
            )

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
    ) -> str:
        """Search for pattern in files using ripgrep.

        Returns a formatted string result for the agent.
        """
        validated_path = self._validate_path(path)
        args = ["--hidden"]

        # Exclude VCS directories
        for dir in self.VCS_DIRECTORIES_TO_EXCLUDE:
            args.extend(["--glob", f"!{dir}"])

        # Limit line length
        args.extend(["--max-columns", "500"])

        # Multiline
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

        # Pattern
        if pattern.startswith("-"):
            args.extend(["-e", pattern])
        else:
            args.append(pattern)

        # File type
        if file_type:
            args.extend(["--type", file_type])

        # Glob patterns
        if glob:
            for raw_pattern in glob.split():
                if "{" in raw_pattern and "}" in raw_pattern:
                    args.extend(["--glob", raw_pattern])
                else:
                    for p in raw_pattern.split(","):
                        if p:
                            args.extend(["--glob", p])

        rg_path = self._find_rg()

        try:
            result = subprocess.run(
                [rg_path] + args + [str(validated_path)],
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return f"Error: Ripgrep search timed out after {self.timeout_seconds} seconds."

        # Exit code 0 = matches found, 1 = no matches (both are success)
        if result.returncode not in (0, 1):
            return f"Error: Ripgrep failed: {result.stderr.strip() or 'unknown error'}"

        lines = [line for line in result.stdout.strip().split("\n") if line]
        cwd = Path.cwd()

        if output_mode == "content":
            limited, applied_limit = self._apply_head_limit(lines, head_limit, offset)
            # Convert absolute paths to relative in ripgrep output
            # Ripgrep output formats with -n when searching directories:
            # - Match line: filepath:linenum:content (sep2 = :)
            # - Context line: filepath:linenum-content or filepath-linenum-content (sep2 = -)
            # The key: find :NN: or :NN- or -NN- pattern, then determine sep type from what follows
            final_lines = []
            for line in limited:
                converted = False
                # Try :NN: or :NN- pattern first (filepath:linenum: or filepath:linenum-)
                m = re.search(r":(\d+)(:|-)(.*)$", line, re.DOTALL)
                if m:
                    linenum = m.group(1)
                    sep2 = m.group(2)  # : for match, - for context
                    content_rest = m.group(3)
                    fp = line[: m.start()]
                    try:
                        rel = Path(fp).relative_to(cwd)
                        if sep2 == ":":
                            final_lines.append(f"{rel}:{linenum}:{content_rest}")
                        else:
                            final_lines.append(f"{rel}:{linenum}-{content_rest}")
                        converted = True
                    except ValueError:
                        pass
                # Try -NN- pattern (filepath-linenum- or filepath-linenum-content)
                if not converted:
                    m = re.search(r"-(\d+)-(.*)$", line, re.DOTALL)
                    if m:
                        linenum = m.group(1)
                        content_rest = m.group(2)
                        fp = line[: m.start()]
                        try:
                            rel = Path(fp).relative_to(cwd)
                            final_lines.append(f"{rel}:{linenum}-{content_rest}")
                            converted = True
                        except ValueError:
                            pass
                if not converted:
                    final_lines.append(line)
            content = "\n".join(final_lines)
            info = ""
            if applied_limit:
                info = f"\n[Showing {applied_limit} results with limit]"
            if offset > 0:
                info += f" [offset: {offset}]"
            return content + info if info else content

        if output_mode == "count":
            limited, applied_limit = self._apply_head_limit(lines, head_limit, offset)
            total = 0
            file_count = 0
            # Convert paths to relative
            count_lines = []
            for line in limited:
                colon_idx = line.rfind(":")
                if colon_idx > 0:
                    fp = line[:colon_idx]
                    count_str = line[colon_idx + 1 :]
                    try:
                        cnt = int(count_str)
                        total += cnt
                        file_count += 1
                        rel = Path(fp).relative_to(cwd)
                        count_lines.append(f"{rel}:{cnt}")
                    except (ValueError, OSError):
                        count_lines.append(line)
                else:
                    count_lines.append(line)
            info = f"\nFound {total} total occurrences across {file_count} files"
            if applied_limit:
                info += f" [limit: {applied_limit}]"
            if offset > 0:
                info += f" [offset: {offset}]"
            return "\n".join(count_lines) + info if count_lines else f"No matches found{info}"

        # files_with_matches mode
        # Sort by mtime
        def get_mtime(p: str) -> float:
            try:
                return os.path.getmtime(p)
            except OSError:
                return 0

        sorted_lines = sorted(lines, key=get_mtime, reverse=True)
        limited, applied_limit = self._apply_head_limit(sorted_lines, head_limit, offset)

        # Convert to relative
        relative_files = []
        for fp in limited:
            try:
                rel = Path(fp).relative_to(cwd)
                relative_files.append(str(rel))
            except ValueError:
                relative_files.append(fp)

        info = f"Found {len(relative_files)} files"
        if applied_limit:
            info += f" [limit: {applied_limit}]"
        if offset > 0:
            info += f" [offset: {offset}]"
        return info + "\n" + "\n".join(relative_files)


def create_grep_tool(
    grep_config: "AgentGrepConfig",
    working_dir: str | None = None,
) -> "GrepTools | None":
    """Create a grep tool based on agent configuration.

    Args:
        grep_config: Agent grep configuration.
        working_dir: Agent's working directory (fallback if grep.base_dir not set).

    Returns:
        A GrepTools instance, or None if grep is disabled.
    """
    if not grep_config.enabled:
        return None

    base_dir = None
    if grep_config.base_dir:
        base_dir = grep_config.base_dir
    elif working_dir:
        base_dir = working_dir

    return GrepTools(
        base_dir=base_dir,
        max_results=grep_config.max_results,
        timeout_seconds=grep_config.timeout_seconds,
    )


if TYPE_CHECKING:
    from ..core.config import AgentGrepConfig
