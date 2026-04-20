"""Secure shell tools wrapper with command filtering and safety checks."""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path
from typing import Any, List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.config import AgentShellConfig


class SecureShellTools:
    """Secure wrapper for shell operations with command filtering."""

    # Dangerous commands that should be blocked
    DANGEROUS_COMMANDS = {
        'rm', 'rmdir', 'mv', 'cp', 'chmod', 'chown', 'chgrp',
        'sudo', 'su', 'doas', 'pkexec',
        'dd', 'mkfs', 'fdisk', 'parted',
        'reboot', 'shutdown', 'halt', 'poweroff',
        'passwd', 'useradd', 'userdel', 'usermod',
        'crontab', 'at', 'batch',
        'iptables', 'ufw', 'firewalld',
        'systemctl', 'service', 'init',
        'mount', 'umount', 'losetup',
        'kill', 'killall', 'pkill',
        'nohup', 'disown', 'screen', 'tmux',
        'curl', 'wget', 'nc', 'netcat', 'telnet', 'ssh',
        'python', 'python3', 'pip', 'pip3', 'npm', 'yarn',
        'docker', 'podman', 'kubectl',
        'git', 'svn', 'hg',
    }

    # Safe commands that are explicitly allowed
    SAFE_COMMANDS = {
        'ls', 'pwd', 'cd', 'echo', 'cat', 'head', 'tail', 'less', 'more',
        'grep', 'find', 'locate', 'which', 'whereis', 'type',
        'date', 'cal', 'uptime', 'whoami', 'id', 'uname', 'df', 'du',
        'ps', 'top', 'htop', 'free', 'lscpu', 'lsblk', 'lsusb', 'lspci',
        'wc', 'sort', 'uniq', 'cut', 'awk', 'sed', 'tr',
        'mkdir', 'touch', 'ln', 'readlink', 'realpath',
        'history', 'alias', 'export', 'env', 'printenv',
        'man', 'help', 'tldr', 'whatis',
        'ping', 'traceroute', 'nslookup', 'dig', 'host',
        'tree', 'file', 'stat', 'hexdump', 'od', 'strings',
    }

    def __init__(self, base_dir: Path | None = None):
        """Initialize secure shell tools.
        
        Args:
            base_dir: The base directory where commands should be executed.
                     If None, uses current working directory.
        """
        self.base_dir = base_dir
        self._shell_tools = None
        self._init_shell_tools()

    def _init_shell_tools(self) -> None:
        """Initialize the underlying Agno ShellTools."""
        try:
            from agno.tools.shell import ShellTools
            self._shell_tools = ShellTools(
                base_dir=self.base_dir,
                enable_run_shell_command=True,
            )
        except ImportError:
            self._shell_tools = None

    def _is_command_safe(self, command: str) -> tuple[bool, str]:
        """Check if a command is safe to execute.
        
        Args:
            command: The command to check.
            
        Returns:
            A tuple of (is_safe, reason).
        """
        # Parse the command to get the base command
        try:
            # Handle shell operators and pipes
            parts = shlex.split(command)
            if not parts:
                return False, "Empty command"
            
            base_cmd = parts[0].strip()
            
            # Remove path prefixes (e.g., /usr/bin/ls -> ls)
            base_cmd = Path(base_cmd).name
            
        except (ValueError, IndexError):
            return False, f"Invalid command syntax: {command}"
        
        # Check if command is in dangerous list
        if base_cmd in self.DANGEROUS_COMMANDS:
            return False, f"Command '{base_cmd}' is blocked for security reasons"
        
        # Check if command is in safe list
        if base_cmd in self.SAFE_COMMANDS:
            return True, f"Command '{base_cmd}' is allowed"
        
        # For unknown commands, be conservative and block them
        return False, f"Command '{base_cmd}' is not in the allowed list"

    def _sanitize_command(self, command: str) -> str:
        """Sanitize a command for safe execution.
        
        Args:
            command: The command to sanitize.
            
        Returns:
            The sanitized command.
        """
        # Basic sanitization
        command = command.strip()
        
        # Remove potentially dangerous shell constructs
        dangerous_patterns = [
            '&&', '||', ';', '|', '&', '>', '>>', '<', '<<',
            '`', '$(', '${', 'eval', 'exec', 'source',
        ]
        
        # Simple check for dangerous patterns
        for pattern in dangerous_patterns:
            if pattern in command:
                raise ValueError(f"Command contains dangerous pattern: {pattern}")
        
        return command

    def run_shell_command(self, command: str) -> str:
        """Run a shell command with safety checks.
        
        Args:
            command: The command to run.
            
        Returns:
            The command output.
            
        Raises:
            ValueError: If the command is not safe.
        """
        # Check if command is safe
        is_safe, reason = self._is_command_safe(command)
        if not is_safe:
            raise ValueError(f"Command blocked: {reason}")
        
        # Sanitize command
        try:
            sanitized_command = self._sanitize_command(command)
        except ValueError as e:
            raise ValueError(f"Command sanitization failed: {e}")
        
        # Execute command
        if self._shell_tools:
            return self._shell_tools.run_shell_command(sanitized_command)
        else:
            # Fallback to subprocess
            try:
                result = subprocess.run(
                    sanitized_command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30,  # Add timeout for safety
                    cwd=self.base_dir or Path.cwd()
                )
                if result.returncode != 0:
                    return f"Command failed with exit code {result.returncode}:\n{result.stderr}"
                return result.stdout
            except subprocess.TimeoutExpired:
                raise ValueError("Command timed out after 30 seconds")
            except Exception as e:
                raise ValueError(f"Command execution failed: {e}")

    def get_available_tools(self) -> list[dict[str, Any]]:
        """Get available tools for Agno integration."""
        if self._shell_tools:
            return self._shell_tools.get_available_tools()
        return []

    def list_safe_commands(self) -> list[str]:
        """List all safe commands."""
        return sorted(self.SAFE_COMMANDS)

    def list_dangerous_commands(self) -> list[str]:
        """List all dangerous commands."""
        return sorted(self.DANGEROUS_COMMANDS)


def create_secure_shell_tool(
    shell_config: "AgentShellConfig",
    working_dir: str | None = None,
) -> SecureShellTools | None:
    """Create a secure shell tool based on agent configuration.

    Args:
        shell_config: Agent shell configuration.
        working_dir: Agent's working directory (fallback if shell.base_dir not set).

    Returns:
        A SecureShellTools instance, or None if shell is disabled.
    """
    if not shell_config.enabled:
        return None

    # Determine base directory: shell.base_dir > working_dir > current dir
    base_dir = None
    if shell_config.base_dir:
        base_dir = Path(shell_config.base_dir)
    elif working_dir is not None:
        base_dir = Path(working_dir)

    return SecureShellTools(base_dir=base_dir)
