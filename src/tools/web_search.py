"""Web search tool factory for Derek Agent Runner."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.config import AgentSearchConfig, WebSearchConfig


SUPPORTED_PROVIDERS = ("tavily", "duckduckgo", "websearch")
WEBSEARCH_BACKENDS = ("duckduckgo", "google", "bing", "brave", "yandex", "yahoo")


def _resolve_api_key(api_key: str | None) -> str | None:
    """Resolve an API key, expanding ${ENV_VAR} references."""
    if api_key and api_key.startswith("${") and api_key.endswith("}"):
        env_var = api_key[2:-1]
        return os.environ.get(env_var)
    return api_key


def create_search_tool(
    global_config: WebSearchConfig,
    agent_config: AgentSearchConfig,
) -> object | None:
    """Create a search tool based on merged global and agent-level config.

    Args:
        global_config: Global web search settings.
        agent_config: Per-agent overrides.

    Returns:
        An Agno tool instance, or None if search is disabled.
    """
    if not agent_config.enabled:
        return None

    provider = agent_config.provider or global_config.provider
    api_key = _resolve_api_key(agent_config.api_key or global_config.api_key)

    if provider == "tavily":
        from agno.tools.tavily import TavilyTools

        if api_key:
            return TavilyTools(api_key=api_key)
        return TavilyTools()

    elif provider == "duckduckgo":
        from agno.tools.duckduckgo import DuckDuckGoTools

        return DuckDuckGoTools()

    elif provider == "websearch":
        from agno.tools.websearch import WebSearchTools

        backend = global_config.backend
        if backend:
            return WebSearchTools(backend=backend)
        return WebSearchTools()

    else:
        raise ValueError(
            f"Unsupported search provider: '{provider}'. "
            f"Choose from: {', '.join(SUPPORTED_PROVIDERS)}"
        )
