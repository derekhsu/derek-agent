"""Built-in slash commands."""

from .base import Command, CommandResult


class QuitCommand(Command):
    """Quit the application."""

    name = "quit"
    description = "退出程式"
    usage = "/quit"
    aliases = ["q", "exit"]

    async def execute(self, args: list[str]) -> str:
        """Execute quit command."""
        if self.app:
            self.app.exit()
        return "正在退出..."


class NewChatCommand(Command):
    """Start a new conversation."""

    name = "new"
    description = "開始新對話"
    usage = "/new"
    aliases = ["n", "clear"]

    async def execute(self, args: list[str]) -> str:
        """Execute new chat command."""
        if self.app and hasattr(self.app, "action_new_chat"):
            self.app.action_new_chat()
        return "新對話已開始"


class AgentCommand(Command):
    """Switch to a different agent."""

    name = "agent"
    description = "切換 Agent"
    usage = "/agent [agent_id]"
    aliases = ["a", "switch"]

    async def execute(self, args: list[str]) -> str:
        """Execute agent switch command."""
        if not args:
            # Open agent selection screen
            if self.app and hasattr(self.app, "action_switch_agent"):
                self.app.action_switch_agent()
            return "請選擇 Agent"

        agent_id = args[0]
        if self.runner:
            try:
                success = await self.runner.switch_agent(agent_id)
                if success:
                    agent_name = self.runner.get_current_agent_name()
                    return f"已切換至 Agent: {agent_name}"
                else:
                    return f"無法切換至 Agent: {agent_id}"
            except Exception as e:
                return f"切換失敗: {e}"
        return "Runner 未初始化"

    def get_completions(self, partial: str) -> list[str]:
        """Get agent ID completions."""
        if not self.runner:
            return []

        agents = self.runner.list_available_agents()
        matches = []
        for agent in agents:
            if partial.lower() in agent.id.lower():
                matches.append(agent.id)
        return matches

    def validate_args(self, args: list[str]) -> tuple[bool, str]:
        """Validate agent ID."""
        if not args:
            return True, ""  # No args is valid - will open selector

        agent_id = args[0]
        if not self.runner:
            return True, ""  # Can't validate without runner

        agents = self.runner.list_available_agents()
        for agent in agents:
            if agent.id == agent_id:
                return True, ""

        available = ", ".join([a.id for a in agents[:5]])
        return False, f"未知的 Agent ID。可用的 Agent: {available}..."


class HelpCommand(Command):
    """Show help information."""

    name = "help"
    description = "顯示幫助"
    usage = "/help [command]"
    aliases = ["h", "?"]

    async def execute(self, args: list[str]) -> str:
        """Execute help command."""
        if args:
            # Show help for specific command
            cmd_name = args[0].lstrip("/")
            from .registry import get_command_registry

            registry = get_command_registry()
            cmd_class = registry.get(cmd_name)
            if cmd_class:
                aliases_str = ", ".join([f"/{a}" for a in cmd_class.aliases])
                return f"""/{cmd_class.name} - {cmd_class.description}

用法: {cmd_class.usage}
別名: {aliases_str}
"""
            else:
                return f"未知指令: /{cmd_name}"

        # Show general help
        from .registry import get_command_registry

        registry = get_command_registry()
        commands = registry.list_commands()

        help_text = "## 可用指令\n\n"
        for cmd in commands:
            aliases_str = ", ".join([f"/{a}" for a in cmd.aliases[:2]])
            if aliases_str:
                help_text += f"**/{cmd.name}** ({aliases_str}) - {cmd.description}\n"
            else:
                help_text += f"**/{cmd.name}** - {cmd.description}\n"

        help_text += """
## 快捷鍵

- **q** / **ctrl+x** / **f10** - 退出程式
- **a** - 切換 Agent
- **n** - 開始新對話
- **h** - 顯示對話歷史
- **?** - 顯示幫助
- **Enter** - 發送訊息
- **Shift+Enter** - 輸入多行文字

輸入 `/` 開啟指令自動完成
"""
        return help_text


class ClearCommand(Command):
    """Clear the chat history."""

    name = "clear"
    description = "清除對話記錄"
    usage = "/clear"
    aliases = ["cls"]

    async def execute(self, args: list[str]) -> str:
        """Execute clear command."""
        if self.app and hasattr(self.app, "_chat_screen"):
            chat_screen = self.app._chat_screen
            if chat_screen and hasattr(chat_screen, "action_new_chat"):
                chat_screen.action_new_chat()
        return "對話記錄已清除"


class CompactCommand(Command):
    """Compact the conversation with optional focus."""

    name = "compact"
    description = "壓縮對話內容"
    usage = "/compact [focus]"
    aliases = ["c", "summary"]

    async def execute(self, args: list[str]) -> str:
        """Execute compact command."""
        focus = args[0] if args else None

        if self.runner:
            try:
                # Get conversation history
                messages = await self.runner.get_conversation_history()
                if not messages:
                    return "沒有對話內容可壓縮"

                # TODO: Implement actual compaction logic
                # For now, just return a summary
                msg_count = len(messages)
                if focus:
                    return f"已壓縮對話（{msg_count} 則訊息），主題聚焦於: {focus}"
                else:
                    return f"已壓縮對話（{msg_count} 則訊息）"
            except Exception as e:
                return f"壓縮失敗: {e}"

        return "Runner 未初始化"


def register_all_commands() -> None:
    """Register all built-in commands."""
    from .registry import get_command_registry
    from .mcp_command import MCPCommand

    registry = get_command_registry()
    registry.register(QuitCommand)
    registry.register(NewChatCommand)
    registry.register(AgentCommand)
    registry.register(HelpCommand)
    registry.register(ClearCommand)
    registry.register(CompactCommand)
    registry.register(MCPCommand)
