"""Tests for file-based skills functionality."""

from pathlib import Path
import tempfile

import pytest
import yaml

from src.core.config import AgentConfig, Config
from src.core.skills import build_agent_skills, resolve_skill_directories


def _write_skill(root: Path, name: str, description: str, instructions: str) -> None:
    skill_dir = root / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        "---\n"
        f"name: {name}\n"
        f"description: {description}\n"
        "---\n\n"
        f"{instructions}\n",
        encoding="utf-8",
    )


class TestResolveSkillDirectories:
    def test_uses_agent_working_dir(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            working_dir = tmp_path / "workspace"
            working_dir.mkdir()

            directories = resolve_skill_directories(
                config_dir=tmp_path / "config",
                working_dir=str(working_dir),
            )

            assert directories.user == (tmp_path / "config" / "skills").resolve()
            assert directories.project == (working_dir / ".derek-agent" / "skills").resolve()


class TestBuildAgentSkills:
    def test_builtin_skills_load_automatically(self):
        """Builtin skills should load without explicit config."""
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            builtin_root = tmp_path / "builtin"
            user_root = tmp_path / "user"
            project_root = tmp_path / "project"

            _write_skill(builtin_root, "auto-skill", "builtin auto", "builtin instructions")

            config = AgentConfig(
                id="coder",
                name="Coder",
                skills=[],  # No explicit skills
            )

            skills = build_agent_skills(
                config,
                builtin_dir=builtin_root,
                user_dir=user_root,
                project_dir=project_root,
            )

            assert skills is not None
            assert "auto-skill" in skills.get_skill_names()
            assert skills.get_skill("auto-skill").description == "builtin auto"

    def test_user_project_skills_require_explicit_config(self):
        """User/project skills only load when listed in config.skills."""
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            builtin_root = tmp_path / "builtin"
            user_root = tmp_path / "user"
            project_root = tmp_path / "project"

            _write_skill(builtin_root, "shared", "builtin", "builtin instructions")
            _write_skill(user_root, "shared", "user", "user instructions")
            _write_skill(project_root, "shared", "project", "project instructions")
            _write_skill(project_root, "project-only", "project only", "project only instructions")

            config = AgentConfig(
                id="coder",
                name="Coder",
                skills=["shared", "project-only"],  # Explicitly request these
            )

            skills = build_agent_skills(
                config,
                builtin_dir=builtin_root,
                user_dir=user_root,
                project_dir=project_root,
            )

            assert skills is not None
            # Builtin loaded automatically + requested user/project skills
            assert set(skills.get_skill_names()) == {"shared", "project-only"}
            # User/project override builtin for same name
            assert skills.get_skill("shared").instructions == "project instructions"
            assert skills.get_skill("shared").description == "project"

    def test_returns_none_when_no_skills_available(self):
        """Returns None only when no builtin, user, or project skills exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            config = AgentConfig(
                id="default",
                name="Default",
                skills=[],
            )

            skills = build_agent_skills(
                config,
                builtin_dir=tmp_path / "builtin",  # Empty/doesn't exist
                user_dir=tmp_path / "user",
                project_dir=tmp_path / "project",
            )

            assert skills is None

    def test_returns_builtin_skills_even_with_empty_config(self):
        """Even with empty config.skills, builtin skills should load."""
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            builtin_root = tmp_path / "builtin"
            user_root = tmp_path / "user"
            project_root = tmp_path / "project"

            _write_skill(builtin_root, "skill-a", "desc a", "instructions a")
            _write_skill(builtin_root, "skill-b", "desc b", "instructions b")

            config = AgentConfig(
                id="default",
                name="Default",
                skills=[],  # Empty
            )

            skills = build_agent_skills(
                config,
                builtin_dir=builtin_root,
                user_dir=user_root,
                project_dir=project_root,
            )

            assert skills is not None
            assert set(skills.get_skill_names()) == {"skill-a", "skill-b"}


class TestConfigSkillInheritance:
    def test_applies_default_skill_inheritance(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            agents_file = tmp_path / "agents.yaml"
            agents_file.write_text(
                yaml.safe_dump(
                    {
                        "agents": [
                            {
                                "id": "default",
                                "name": "Default",
                                "skills": ["shared", "default-only"],
                            },
                            {
                                "id": "coder",
                                "name": "Coder",
                                "skills": ["shared", "code-review"],
                            },
                            {
                                "id": "standalone",
                                "name": "Standalone",
                                "skills": ["local-only"],
                                "inherit_default_skills": False,
                            },
                        ]
                    },
                    allow_unicode=True,
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            config = Config(config_dir=tmp_path)
            agents = {agent.id: agent for agent in config.agents}

            assert agents["coder"].skills == ["shared", "code-review", "default-only"]
            assert agents["standalone"].skills == ["local-only"]
