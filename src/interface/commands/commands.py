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


class HistoryCommand(Command):
    """Show conversation history."""

    name = "history"
    description = "顯示對話歷史"
    usage = "/history"
    aliases = ["h", "hist"]

    async def execute(self, args: list[str]) -> str:
        """Execute history command."""
        if self.app and hasattr(self.app, "action_history"):
            self.app.action_history()
            return ""  # Return empty as the screen will handle the UI
        return "無法開啟對話歷史"


class CompactCommand(Command):
    """Compact the conversation with optional focus."""

    name = "compact"
    description = "壓縮對話內容"
    usage = "/compact [auto|manual|threshold <n>|status]"
    aliases = ["c", "summary"]

    async def execute(self, args: list[str]) -> str:
        """Execute compact command."""
        if not self.runner:
            return "Runner 未初始化"

        try:
            # Handle subcommands
            if args:
                subcommand = args[0].lower()

                if subcommand == "auto":
                    await self.runner.update_compression_config(auto_trigger=True)
                    return "✅ 已啟用自動壓縮提示（達到閾值時自動建議）"

                elif subcommand == "manual":
                    await self.runner.update_compression_config(auto_trigger=False)
                    return "✅ 已設為手動模式（僅透過 /compact 觸發）"

                elif subcommand == "threshold" and len(args) >= 2:
                    try:
                        percent = int(args[1])
                        if 1 <= percent <= 100:
                            await self.runner.update_compression_config(threshold_percent=percent)
                            return f"✅ 已設定壓縮閾值為 {percent}%"
                        else:
                            return "❌ 閾值必須在 1-100 之間"
                    except ValueError:
                        return "❌ 請提供有效的數字（1-100）"

                elif subcommand == "status":
                    config = self.runner.get_compression_config()
                    return (
                        f"📊 壓縮設定狀態\n"
                        f"- 啟用狀態: {'✅' if config['enabled'] else '❌'}\n"
                        f"- 觸發模式: {'自動' if config['auto_trigger'] else '手動'}\n"
                        f"- 閾值百分比: {config['threshold_percent']}%\n"
                        f"- 摘要模型: {config['summary_model'] or '使用當前模型'}\n"
                        f"- 摘要上限: {config['max_summary_tokens']} tokens"
                    )

                elif subcommand in ("on", "enable"):
                    await self.runner.update_compression_config(enabled=True)
                    return "✅ 已啟用對話壓縮功能"

                elif subcommand in ("off", "disable"):
                    await self.runner.update_compression_config(enabled=False)
                    return "✅ 已停用對話壓縮功能"

            # Default: execute compression
            result = await self.runner.compress_conversation()

            if result["success"]:
                msg_count = result["message_count"]
                return f"✅ 對話已壓縮（{msg_count} 則訊息已摘要為系統提示）"
            else:
                error = result.get("error", "未知錯誤")
                return f"❌ 壓縮失敗: {error}"

        except Exception as e:
            return f"❌ 壓縮失敗: {e}"

    def get_completions(self, partial: str) -> list[str]:
        """Get command completions."""
        subcommands = ["auto", "manual", "threshold", "status", "on", "off", "enable", "disable"]
        if not partial:
            return subcommands
        return [cmd for cmd in subcommands if cmd.startswith(partial.lower())]


def register_all_commands() -> None:
    """Register all built-in commands."""
    from .registry import get_command_registry
    from .mcp_command import MCPCommand
    from .skills_command import SkillsCommand
    from .memories_command import MemoriesCommand

    registry = get_command_registry()
    registry.register(QuitCommand)
    registry.register(NewChatCommand)
    registry.register(AgentCommand)
    registry.register(HelpCommand)
    registry.register(ClearCommand)
    registry.register(HistoryCommand)
    registry.register(CompactCommand)
    registry.register(MCPCommand)
    registry.register(SkillsCommand)
    registry.register(MemoriesCommand)
