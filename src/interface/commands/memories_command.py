"""Memories listing slash command."""

from .base import Command


class MemoriesCommand(Command):
    """List stored memories for the current agent."""

    name = "memories"
    description = "列出目前 Agent 記住的用戶記憶"
    usage = "/memories"
    aliases = ["memory", "mem"]

    async def execute(self, args: list[str]) -> str:
        """Execute memories command."""
        if not self.runner:
            return "Runner 未初始化"

        memories = self.runner.get_current_agent_memories()
        if memories is None:
            return "目前沒有載入的 Agent"

        if not memories:
            return "目前沒有記憶（試著告訴 Agent 你的名字或偏好）"

        lines = ["## 記憶\n"]
        for i, mem in enumerate(memories, 1):
            memory_text = mem.get("memory", "未知記憶")
            lines.append(f"{i}. {memory_text}")
        return "\n".join(lines)
