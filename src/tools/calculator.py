"""Calculator tool factory for Derek Agent Runner."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.config import AgentCalculatorConfig


def create_calculator_tool(
    calculator_config: "AgentCalculatorConfig",
) -> "CalculatorTools | None":
    """Create a calculator tool based on agent configuration.

    Args:
        calculator_config: Agent calculator configuration.

    Returns:
        An Agno CalculatorTools instance, or None if calculator is disabled.
    """
    if not calculator_config.enabled:
        return None

    from agno.tools.calculator import CalculatorTools

    return CalculatorTools()
