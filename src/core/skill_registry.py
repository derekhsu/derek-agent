"""Skill registry for Derek Agent Runner."""

import importlib
import pkgutil
from typing import Any, Callable

from agno.tools.toolkit import Toolkit

from .config import logger


class SkillInfo:
    """Information about a registered skill."""

    def __init__(
        self,
        name: str,
        skill: Toolkit | Callable,
        description: str | None = None,
        source: str | None = None,
    ):
        self.name = name
        self.skill = skill
        self.description = description or ""
        self.source = source or "unknown"

    def get_toolkit(self) -> Toolkit | None:
        """Get the skill as a Toolkit if applicable."""
        if isinstance(self.skill, Toolkit):
            return self.skill
        return None


class SkillRegistry:
    """Registry for managing skills/tools."""

    def __init__(self):
        """Initialize skill registry."""
        self._skills: dict[str, SkillInfo] = {}
        self._discover_builtin_skills()

    def _discover_builtin_skills(self) -> None:
        """Discover and register builtin skills."""
        try:
            from .. import skills as skills_module

            for importer, modname, ispkg in pkgutil.iter_modules(
                skills_module.__path__, skills_module.__name__ + "."
            ):
                try:
                    module = importlib.import_module(modname)
                    self._register_from_module(module)
                except Exception as e:
                    logger.warning(f"Failed to load skill module {modname}: {e}")
        except ImportError:
            logger.debug("No builtin skills package found")

    def _register_from_module(self, module: Any) -> None:
        """Register skills from a module."""
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            # Check if it's a Toolkit subclass
            if (
                isinstance(attr, type)
                and issubclass(attr, Toolkit)
                and attr is not Toolkit
            ):
                try:
                    instance = attr()
                    self.register(attr_name, instance, source=module.__name__)
                except Exception as e:
                    logger.warning(f"Failed to instantiate {attr_name}: {e}")

    def register(
        self,
        name: str,
        skill: Toolkit | Callable,
        description: str | None = None,
        source: str | None = None,
    ) -> None:
        """Register a skill.

        Args:
            name: Unique name for the skill.
            skill: The skill instance or function.
            description: Optional description.
            source: Source module or origin.
        """
        self._skills[name] = SkillInfo(
            name=name,
            skill=skill,
            description=description,
            source=source,
        )

    def unregister(self, name: str) -> bool:
        """Unregister a skill.

        Args:
            name: Skill name to unregister.

        Returns:
            True if skill was found and removed.
        """
        if name in self._skills:
            del self._skills[name]
            return True
        return False

    def get(self, name: str) -> SkillInfo | None:
        """Get skill info by name.

        Args:
            name: Skill name.

        Returns:
            SkillInfo or None if not found.
        """
        return self._skills.get(name)

    def get_toolkit(self, name: str) -> Toolkit | None:
        """Get a skill as Toolkit.

        Args:
            name: Skill name.

        Returns:
            Toolkit instance or None.
        """
        info = self._skills.get(name)
        if info:
            return info.get_toolkit()
        return None

    def list_skills(self) -> list[SkillInfo]:
        """List all registered skills.

        Returns:
            List of SkillInfo objects.
        """
        return list(self._skills.values())

    def has_skill(self, name: str) -> bool:
        """Check if a skill is registered.

        Args:
            name: Skill name.

        Returns:
            True if skill is registered.
        """
        return name in self._skills

    def resolve_skill_references(self, skill_refs: list[str]) -> list[Toolkit]:
        """Resolve skill references to Toolkit instances.

        Args:
            skill_refs: List of skill names (e.g., ["builtin:web_search", "custom:my_tool"])

        Returns:
            List of Toolkit instances.
        """
        toolkits: list[Toolkit] = []

        for ref in skill_refs:
            # Handle prefix notation (e.g., "builtin:web_search")
            if ":" in ref:
                prefix, name = ref.split(":", 1)
            else:
                name = ref

            skill = self.get_toolkit(name)
            if skill:
                toolkits.append(skill)
            else:
                logger.warning(f"Skill not found: {ref}")

        return toolkits


# Global registry instance
_registry: SkillRegistry | None = None


def get_skill_registry() -> SkillRegistry:
    """Get global skill registry."""
    global _registry
    if _registry is None:
        _registry = SkillRegistry()
    return _registry


def reset_skill_registry() -> None:
    """Reset global skill registry (mainly for testing)."""
    global _registry
    _registry = None
