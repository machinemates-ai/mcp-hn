"""
HN-MCP Server - FastMCP Implementation.

A comprehensive MCP server for Hacker News with:
- Tools: Search, get stories, get user info, fetch article content
- Resources: hackernews:// URIs for story feeds
- Prompts: Templates for common HN analysis tasks
- Caching: LRU cache with adaptive TTLs
- Async: Full async/await with httpx
"""

import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from hn_mcp.cache import get_cache
from hn_mcp.content import ContentExtractionError, fetch_article_content
from hn_mcp.hn import HNClient

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastMCP) -> AsyncIterator[None]:
    """Initialize server resources on startup."""
    logger.info("Starting hn-mcp server...")
    yield
    logger.info("Shutting down hn-mcp server...")


# Create FastMCP server with lifespan
mcp = FastMCP(
    name="hn-mcp",
    lifespan=lifespan,
    instructions="""
    HN-MCP provides access to Hacker News via MCP.

    Available capabilities:
    - Tools: get_stories, search_stories, get_story_info, get_user_info
    - Resources: Access story feeds via hackernews:// URIs
    - Prompts: Templates for news analysis and summarization

    For browsing stories, use the hackernews:// resources.
    For specific queries, use the search_stories tool.
    """,
)


# =============================================================================
# TOOLS (all read-only)
# =============================================================================


@mcp.tool(
    name="get_stories",
    description=(
        "Get stories from Hacker News. "
        "Options are `top`, `new`, `ask`, `show`, `job` for types of stories. "
        "This doesn't include comments. Use `get_story_info` to get comments."
    ),
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def get_stories(
    story_type: str = "top",
    num_stories: int = 10,
) -> str:
    """
    Fetch Hacker News stories by type.

    Args:
        story_type: Type of stories - 'top', 'new', 'ask', 'show', 'job'
        num_stories: Number of stories to get (default: 10)
    """
    num_stories = min(max(1, num_stories), 50)

    async with HNClient() as client:
        stories = await client.get_stories(story_type, num_stories)

    return json.dumps(stories, indent=2)


@mcp.tool(
    name="search_stories",
    description=(
        "Search stories from Hacker News. "
        "It is generally recommended to use simpler queries (< 5 words). "
        "Very targeted queries may not return any results."
    ),
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def search_stories(
    query: str,
    num_results: int = 10,
    search_by_date: bool = False,
) -> str:
    """
    Search Hacker News stories.

    Args:
        query: Search query (keep it simple, < 5 words recommended)
        num_results: Number of results (default: 10)
        search_by_date: If True, sort by date; else by relevance
    """
    num_results = min(max(1, num_results), 50)

    async with HNClient() as client:
        results = await client.search_stories(query, num_results, search_by_date)

    return json.dumps(results, indent=2)


@mcp.tool(
    name="get_story_info",
    description="Get detailed story info from Hacker News, including the comments",
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def get_story_info(story_id: int) -> str:
    """
    Get detailed information about a specific story.

    Args:
        story_id: The Hacker News story ID
    """
    async with HNClient() as client:
        story = await client.get_story_info(story_id)

    return json.dumps(story, indent=2)


@mcp.tool(
    name="get_user_info",
    description=(
        "Get user info from Hacker News, including the stories they've submitted"
    ),
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def get_user_info(
    user_name: str,
    num_stories: int = 10,
) -> str:
    """
    Get information about a Hacker News user.

    Args:
        user_name: The HN username
        num_stories: Number of stories to include (default: 10)
    """
    num_stories = min(max(1, num_stories), 30)

    async with HNClient() as client:
        user = await client.get_user_info(user_name, num_stories)

    return json.dumps(user, indent=2)


# =============================================================================
# Additional tools
# =============================================================================


@mcp.tool(
    name="fetch_article_content",
    description="Fetch and extract article content as Markdown from a story's URL",
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def tool_fetch_article_content(url: str) -> str:
    """
    Fetch article content and convert to Markdown.

    Args:
        url: The article URL to fetch
    """
    try:
        result = await fetch_article_content(url)
        return json.dumps(result, indent=2)
    except ContentExtractionError as e:
        return json.dumps({"error": str(e)})


@mcp.tool(
    name="cache_stats",
    description="Get cache statistics for debugging and monitoring",
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def cache_stats() -> str:
    """Get current cache statistics."""
    stats = get_cache().stats()
    return json.dumps(stats, indent=2)


# =============================================================================
# RESOURCES - hackernews:// URIs
# =============================================================================


@mcp.resource(
    uri="hackernews://top",
    name="Top Stories",
    description="Top stories currently on Hacker News front page",
    mime_type="application/json",
)
async def resource_top_stories() -> str:
    """Get top stories from HN front page."""
    async with HNClient() as client:
        stories = await client.get_stories("top", 30)
    return json.dumps(stories, indent=2)


@mcp.resource(
    uri="hackernews://new",
    name="New Stories",
    description="Newest stories on Hacker News",
    mime_type="application/json",
)
async def resource_new_stories() -> str:
    """Get newest stories."""
    async with HNClient() as client:
        stories = await client.get_stories("new", 30)
    return json.dumps(stories, indent=2)


@mcp.resource(
    uri="hackernews://ask",
    name="Ask HN",
    description="Ask HN posts - questions from the community",
    mime_type="application/json",
)
async def resource_ask_stories() -> str:
    """Get Ask HN posts."""
    async with HNClient() as client:
        stories = await client.get_stories("ask_hn", 30)
    return json.dumps(stories, indent=2)


@mcp.resource(
    uri="hackernews://show",
    name="Show HN",
    description="Show HN posts - projects shared by the community",
    mime_type="application/json",
)
async def resource_show_stories() -> str:
    """Get Show HN posts."""
    async with HNClient() as client:
        stories = await client.get_stories("show_hn", 30)
    return json.dumps(stories, indent=2)


@mcp.resource(
    uri="hackernews://jobs",
    name="Jobs",
    description="Job postings on Hacker News",
    mime_type="application/json",
)
async def resource_job_stories() -> str:
    """Get job postings."""
    async with HNClient() as client:
        stories = await client.get_stories("job", 30)
    return json.dumps(stories, indent=2)


@mcp.resource(
    uri="hackernews://story/{story_id}",
    name="Story Details",
    description="Get detailed information about a specific story with comments",
    mime_type="application/json",
)
async def resource_story_detail(story_id: str) -> str:
    """Get story details by ID."""
    async with HNClient() as client:
        story = await client.get_story_info(int(story_id))
    return json.dumps(story, indent=2)


@mcp.resource(
    uri="hackernews://user/{username}",
    name="User Profile",
    description="Get user profile and recent submissions",
    mime_type="application/json",
)
async def resource_user_profile(username: str) -> str:
    """Get user profile."""
    async with HNClient() as client:
        user = await client.get_user_info(username)
    return json.dumps(user, indent=2)


# =============================================================================
# PROMPTS - Reusable prompt templates
# =============================================================================


@mcp.prompt(
    name="summarize_hn",
    description="Summarize the current top stories on Hacker News",
)
async def prompt_summarize_hn() -> str:
    """Generate a prompt for summarizing HN top stories."""
    async with HNClient() as client:
        stories = await client.get_stories("top", 10)

    stories_text = "\n".join(
        f"- [{s.get('title', 'Untitled')}]({s.get('url', '')})"
        f" by {s.get('author', 'unknown')} ({s.get('points', 0)} points)"
        for s in stories
    )

    return f"""Summarize these top Hacker News stories:

{stories_text}

Please provide:
1. A brief overview of the main topics
2. Any emerging trends you notice
3. The most significant/interesting stories"""


@mcp.prompt(
    name="analyze_discussion",
    description="Analyze the discussion and comments on a HN story",
)
async def prompt_analyze_discussion(story_id: int) -> str:
    """Generate a prompt for analyzing a HN discussion."""
    async with HNClient() as client:
        story = await client.get_story_info(story_id)

    return f"""Analyze this Hacker News discussion:

**Story**: {story.get('title', 'Untitled')}
**URL**: {story.get('url', 'N/A')}
**Points**: {story.get('points', 0)}
**Author**: {story.get('author', 'unknown')}

**Comments**:
{json.dumps(story.get('comments', []), indent=2)}

Please analyze:
1. Main points of agreement/disagreement
2. Key insights from commenters
3. Overall sentiment and tone
4. Any expert perspectives shared"""


# =============================================================================
# Entry point - matches original mcp-hn
# =============================================================================


def main() -> None:
    """Run the MCP-HN server."""
    mcp.run()


if __name__ == "__main__":
    main()
