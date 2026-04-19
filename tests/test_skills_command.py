"""Tests for /skills slash command."""

import pytest

from src.interface.commands.registry import CommandRegistry, reset_command_registry
from src.interface.commands.commands import register_all_commands
from src.interface.commands.registry import get_command_registry


class _RunnerWithSkills:
    def __init__(self, skills=None):
        self._skills = skills

    def get_current_agent_skills(self):
        return self._skills


@pytest.fixture
def registry():
    """Create a fresh command registry for each test."""
    reset_command_registry()
    register_all_commands()
    return get_command_registry()


class TestSkillsCommand:
    async def test_lists_current_agent_skills(self, registry):
        result = await registry.execute(
            "skills",
            [],
            runner=_RunnerWithSkills(
                [
                    {"name": "code-review", "description": "Review code quality"},
                    {"name": "debug-python", "description": "Debug Python issues"},
                ]
            ),
        )

        assert result.success is True
        assert "## Skills" in result.message
        assert "**code-review** - Review code quality" in result.message
        assert "**debug-python** - Debug Python issues" in result.message

    async def test_handles_no_loaded_agent(self, registry):
        result = await registry.execute("skills", [], runner=_RunnerWithSkills(None))

        assert result.success is True
        assert result.message == "目前沒有載入的 Agent"

    async def test_handles_empty_skills(self, registry):
        result = await registry.execute("skills", [], runner=_RunnerWithSkills([]))

        assert result.success is True
        assert result.message == "目前 Agent 沒有可用的 skills"
