"""Skills listing slash command."""

from .base import Command


class SkillsCommand(Command):
    """List available skills for the current agent."""

    name = "skills"
    description = "列出目前 Agent 可用的 skills"
    usage = "/skills"
    aliases = ["skill"]

    async def execute(self, args: list[str]) -> str:
        """Execute skills command."""
        if not self.runner:
            return "Runner 未初始化"

        skills = self.runner.get_current_agent_skills()
        if skills is None:
            return "目前沒有載入的 Agent"

        if not skills:
            return "目前 Agent 沒有可用的 skills"

        lines = ["## Skills\n"]
        for skill in skills:
            description = skill["description"] or "無描述"
            lines.append(f"- **{skill['name']}** - {description}")
        return "\n".join(lines)
