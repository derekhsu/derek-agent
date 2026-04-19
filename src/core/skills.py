from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agno.skills import LocalSkills, Skills

from .config import AgentConfig, get_config, logger


@dataclass(frozen=True)
class SkillDirectories:
    builtin: Path
    user: Path
    project: Path


def resolve_skill_directories(
    config_dir: str | Path | None = None,
    working_dir: str | None = None,
) -> SkillDirectories:
    if config_dir is None:
        resolved_config_dir = get_config().config_dir.resolve()
    else:
        resolved_config_dir = Path(config_dir).resolve()

    if working_dir is None:
        project_root = Path.cwd().resolve()
    else:
        project_root = Path(working_dir).resolve()

    builtin_dir = Path(__file__).resolve().parent.parent / "skills" / "builtin"
    user_dir = resolved_config_dir / "skills"
    project_dir = project_root / ".derek-agent" / "skills"

    return SkillDirectories(
        builtin=builtin_dir.resolve(),
        user=user_dir.resolve(),
        project=project_dir.resolve(),
    )


def _load_builtin_skills(builtin_dir: Path) -> Skills | None:
    """Load all builtin skills automatically."""
    if not builtin_dir.exists():
        return None
    return Skills(loaders=[LocalSkills(str(builtin_dir))])


def _load_user_project_skills(
    requested_names: list[str],
    user_dir: Path,
    project_dir: Path,
) -> Skills | None:
    """Load only requested user/project skills."""
    loaders = []
    for directory in (user_dir, project_dir):
        if directory.exists():
            loaders.append(LocalSkills(str(directory)))

    if not loaders or not requested_names:
        return None

    all_skills = Skills(loaders=loaders)
    selected_skills = {}

    for skill_name in requested_names:
        skill = all_skills.get_skill(skill_name)
        if skill:
            selected_skills[skill_name] = skill

    if not selected_skills:
        return None

    all_skills._skills = selected_skills
    return all_skills


def build_agent_skills(
    config: AgentConfig,
    *,
    config_dir: str | Path | None = None,
    builtin_dir: str | Path | None = None,
    user_dir: str | Path | None = None,
    project_dir: str | Path | None = None,
) -> Skills | None:
    """Build agent skills with automatic builtin loading.

    Rules:
    - Builtin skills: automatically load ALL from src/skills/builtin/
    - User/Project skills: only load those explicitly listed in config.skills
    """
    directories = resolve_skill_directories(
        config_dir=config_dir,
        working_dir=config.working_dir,
    )

    resolved_builtin_dir = Path(builtin_dir).resolve() if builtin_dir is not None else directories.builtin
    resolved_user_dir = Path(user_dir).resolve() if user_dir is not None else directories.user
    resolved_project_dir = Path(project_dir).resolve() if project_dir is not None else directories.project

    # Load builtin skills automatically
    builtin_skills = _load_builtin_skills(resolved_builtin_dir)

    # Load requested user/project skills
    user_project_skills = _load_user_project_skills(
        config.skills,
        resolved_user_dir,
        resolved_project_dir,
    )

    # Merge skills (user/project override builtin if same name)
    merged_skills: dict[str, Any] = {}

    if builtin_skills:
        for name, skill in builtin_skills._skills.items():
            merged_skills[name] = skill

    if user_project_skills:
        for name, skill in user_project_skills._skills.items():
            merged_skills[name] = skill

        # Log missing requested skills
        available = set(user_project_skills._skills.keys())
        requested = set(config.skills)
        missing = requested - available
        if missing:
            logger.warning(
                f"Agent {config.id} references missing user/project skills: {', '.join(missing)}"
            )

    if not merged_skills:
        return None

    # Create merged Skills object
    result = Skills(loaders=[])
    result._skills = merged_skills
    return result
