"""Crawler tool factory for Derek Agent Runner."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.config import AgentCrawlerConfig


def create_crawler_tool(
    crawler_config: "AgentCrawlerConfig",
) -> object | None:
    """Create a crawler tool based on agent configuration.

    Args:
        crawler_config: Agent crawler configuration.

    Returns:
        An Agno TrafilaturaTools instance, or None if crawler is disabled.
    """
    if not crawler_config.enabled:
        return None

    from agno.tools.trafilatura import TrafilaturaTools

    return TrafilaturaTools(
        output_format=crawler_config.output_format or "markdown",
        include_comments=True,
        include_tables=True,
        include_images=False,
        include_formatting=True,  # Enable formatting for markdown
        include_links=True,  # Enable links for better context
        with_metadata=True,  # Include metadata for better context
        favor_precision=False,
        favor_recall=True,  # Favor recall for better coverage
        target_language=crawler_config.target_language,
        deduplicate=True,
        max_crawl_urls=crawler_config.max_urls or 10,
    )
