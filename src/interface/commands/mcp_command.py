"""MCP server management slash command."""

from .base import Command


class MCPCommand(Command):
    """Manage MCP servers for the current agent."""

    name = "mcp"
    description = "管理 MCP servers (顯示/停用/啟用)"
    usage = "/mcp [list|disable <name>|enable <name>]"
    aliases = []

    async def execute(self, args: list[str]) -> str:
        """Execute MCP command."""
        if not self.runner:
            return "Runner 未初始化"

        # Get current MCP status
        status = self.runner.get_mcp_status()
        if status is None:
            return "目前沒有載入的 Agent"

        subcommand = args[0] if args else "list"

        if subcommand == "list":
            return self._format_status(status)

        if subcommand == "disable":
            if len(args) < 2:
                return "請指定要停用的 MCP server 名稱: /mcp disable <name>"
            name = args[1]
            if name not in status:
                available = ", ".join(status.keys()) if status else "無"
                return f"未知的 MCP server: {name}。可用的 servers: {available}"
            if not status[name]["enabled"]:
                return f"MCP server '{name}' 已經是停用狀態"
            success = self.runner.disable_mcp_server(name)
            if success:
                return f"已停用 MCP server: {name} (僅當前 session 有效)"
            return f"停用 MCP server 失敗: {name}"

        if subcommand == "enable":
            if len(args) < 2:
                return "請指定要啟用的 MCP server 名稱: /mcp enable <name>"
            name = args[1]
            if name not in status:
                available = ", ".join(status.keys()) if status else "無"
                return f"未知的 MCP server: {name}。可用的 servers: {available}"
            if status[name]["enabled"]:
                return f"MCP server '{name}' 已經是啟用狀態"
            success = self.runner.enable_mcp_server(name)
            if success:
                return f"已啟用 MCP server: {name}"
            return f"啟用 MCP server 失敗: {name}"

        return f"未知子指令: {subcommand}。可用: list, disable, enable"

    def _format_status(self, status: dict[str, dict]) -> str:
        """Format MCP status for display."""
        if not status:
            return "目前 Agent 沒有設定任何 MCP servers"

        lines = ["## MCP Servers 狀態\\n"]
        for name, info in status.items():
            enabled_icon = "🟢" if info["enabled"] else "🔴"
            connected_icon = "✅" if info["connected"] else "❌"
            lines.append(f"{enabled_icon} **{name}** - 啟用: {enabled_icon}, 連線: {connected_icon}")

        lines.append("\\n🟢 = 啟用, 🔴 = 停用, ✅ = 已連線, ❌ = 未連線")
        lines.append("\\n使用 `/mcp disable <name>` 暫時停用")
        lines.append("使用 `/mcp enable <name>` 重新啟用")
        return "\\n".join(lines)

    def get_completions(self, partial: str) -> list[str]:
        """Get completion suggestions."""
        subcommands = ["list", "disable", "enable"]

        # If no runner or no partial, suggest subcommands
        if not self.runner:
            return [s for s in subcommands if s.startswith(partial.lower())]

        words = partial.split()

        # First word: suggest subcommands
        if len(words) == 1 and not partial.endswith(" "):
            return [s for s in subcommands if s.startswith(words[0].lower())]

        # Second word for disable/enable: suggest server names
        if len(words) >= 1:
            subcommand = words[0].lower()
            if subcommand in ("disable", "enable"):
                status = self.runner.get_mcp_status()
                if status:
                    server_names = list(status.keys())
                    prefix = words[1] if len(words) > 1 else ""
                    return [n for n in server_names if n.startswith(prefix)]

        return []

    def validate_args(self, args: list[str]) -> tuple[bool, str]:
        """Validate arguments."""
        if not args:
            return True, ""

        subcommand = args[0].lower()
        valid_subcommands = ["list", "disable", "enable"]

        if subcommand not in valid_subcommands:
            return False, f"未知子指令: {subcommand}. 可用: {', '.join(valid_subcommands)}"

        if subcommand in ("disable", "enable") and len(args) < 2:
            return False, f"請指定 MCP server 名稱: /mcp {subcommand} <name>"

        return True, ""
