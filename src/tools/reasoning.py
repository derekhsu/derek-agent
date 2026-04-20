"""Reasoning tool factory for Derek Agent Runner."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.config import AgentReasoningConfig


def create_reasoning_tool(
    reasoning_config: "AgentReasoningConfig",
) -> "ReasoningTools | None":
    """Create a reasoning tool based on agent configuration.

    Args:
        reasoning_config: Agent reasoning configuration.

    Returns:
        An Agno ReasoningTools instance, or None if reasoning is disabled.
    """
    if not reasoning_config.enabled:
        return None

    from agno.tools.reasoning import ReasoningTools

    return ReasoningTools()
