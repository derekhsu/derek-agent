"""MCP Client manager for Derek Agent Runner."""

import asyncio
from typing import Any

from agno.tools.mcp import MCPTools

from .config import MCPConfig, logger


class MCPConnection:
    """Wrapper for an MCP server connection."""

    def __init__(self, config: MCPConfig):
        """Initialize MCP connection.

        Args:
            config: MCP server configuration.
        """
        self.config = config
        self._tools: MCPTools | None = None
        self._connected = False

    async def connect(self) -> MCPTools:
        """Connect to the MCP server.

        Returns:
            MCPTools instance.
        """
        if self._tools is None:
            if self.config.command:
                # Combine command and args for the full command
                if self.config.args:
                    full_command = f"{self.config.command} {' '.join(self.config.args)}"
                else:
                    full_command = self.config.command
                self._tools = MCPTools(command=full_command, tool_name_prefix=self.config.name)
            elif self.config.url:
                self._tools = MCPTools(
                    transport=self.config.transport,
                    url=self.config.url,
                    tool_name_prefix=self.config.name,
                )
            else:
                raise ValueError("MCP config must have 'command' or 'url'")

            await self._tools.connect()
            self._connected = True

        return self._tools

    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        if self._tools and self._connected:
            await self._tools.close()
            self._connected = False
            self._tools = None

    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._connected

    @property
    def tools(self) -> MCPTools | None:
        """Get MCPTools instance."""
        return self._tools


class MCPClientManager:
    """Manager for MCP client connections."""

    def __init__(self):
        """Initialize MCP client manager."""
        self._connections: dict[str, MCPConnection] = {}
        self._disabled_servers: set[str] = set()
        self._server_configs: dict[str, MCPConfig] = {}

    async def add_server(self, config: MCPConfig) -> MCPConnection:
        """Add and connect to an MCP server.

        Args:
            config: MCP server configuration.

        Returns:
            MCPConnection instance.
        """
        connection = MCPConnection(config)
        self._connections[config.name] = connection
        self._server_configs[config.name] = config
        await connection.connect()
        logger.info(f"Connected to MCP server: {config.name}")
        return connection

    async def remove_server(self, name: str) -> bool:
        """Remove and disconnect an MCP server.

        Args:
            name: MCP server name.

        Returns:
            True if server was found and removed.
        """
        connection = self._connections.get(name)
        if connection:
            await connection.disconnect()
            del self._connections[name]
            logger.info(f"Disconnected from MCP server: {name}")
            return True
        return False

    def get_server(self, name: str) -> MCPConnection | None:
        """Get a server connection by name.

        Args:
            name: MCP server name.

        Returns:
            MCPConnection or None.
        """
        return self._connections.get(name)

    def resolve_tool_name(self, tool_name: str | None) -> tuple[str | None, str | None]:
        if not tool_name:
            return None, None
        for server_name in self._connections:
            prefix = f"{server_name}_"
            if tool_name.startswith(prefix):
                return server_name, tool_name[len(prefix):]
        return None, tool_name

    def is_mcp_tool_name(self, tool_name: str | None) -> bool:
        server_name, _ = self.resolve_tool_name(tool_name)
        return server_name is not None

    def get_all_tools(self) -> list[MCPTools]:
        """Get all connected MCPTools (excluding disabled).

        Returns:
            List of MCPTools instances.
        """
        tools = []
        for name, connection in self._connections.items():
            if name in self._disabled_servers:
                continue
            if connection.tools:
                tools.append(connection.tools)
        return tools

    async def setup_from_config(self, configs: list[MCPConfig]) -> list[MCPTools]:
        """Setup connections from configuration list.

        Args:
            configs: List of MCP configurations.

        Returns:
            List of connected MCPTools.
        """
        all_tools: list[MCPTools] = []

        for config in configs:
            try:
                connection = await self.add_server(config)
                if connection.tools:
                    all_tools.append(connection.tools)
            except Exception as e:
                logger.error(f"Failed to connect to MCP server {config.name}: {e}")

        return all_tools

    async def close_all(self) -> None:
        """Close all MCP connections."""
        for name, connection in list(self._connections.items()):
            try:
                await connection.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting from {name}: {e}")
        self._connections.clear()

    def list_servers(self) -> list[str]:
        """List all connected server names.

        Returns:
            List of server names.
        """
        return list(self._connections.keys())

    def disable_server(self, name: str) -> bool:
        """Temporarily disable an MCP server (session only).

        Args:
            name: MCP server name.

        Returns:
            True if server was found and disabled.
        """
        if name in self._connections:
            self._disabled_servers.add(name)
            logger.info(f"Disabled MCP server (session only): {name}")
            return True
        return False

    def enable_server(self, name: str) -> bool:
        """Re-enable a disabled MCP server.

        Args:
            name: MCP server name.

        Returns:
            True if server was found and enabled.
        """
        if name in self._disabled_servers:
            self._disabled_servers.discard(name)
            logger.info(f"Enabled MCP server: {name}")
            return True
        return False

    def get_server_status(self) -> dict[str, dict]:
        """Get status of all MCP servers.

        Returns:
            Dict mapping server name to status info.
        """
        status = {}
        for name in self._connections:
            status[name] = {
                "enabled": name not in self._disabled_servers,
                "connected": self._connections[name].is_connected,
            }
        return status


# Global manager instance
_manager: MCPClientManager | None = None


def get_mcp_manager() -> MCPClientManager:
    """Get global MCP client manager."""
    global _manager
    if _manager is None:
        _manager = MCPClientManager()
    return _manager


def reset_mcp_manager() -> None:
    """Reset global MCP client manager."""
    global _manager
    _manager = None
