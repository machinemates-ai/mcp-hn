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
from hn_mcp.rate_limit import get_rate_limiter

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
    description=(
        "Get detailed story info from Hacker News, including the comments. "
        "Use include_comments=False for just the story metadata. "
        "Use comment_depth to control how deep to fetch nested replies (1-10)."
    ),
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def get_story_info(
    story_id: int,
    include_comments: bool = True,
    comment_depth: int = 3,
    max_comments: int = 20,
) -> str:
    """
    Get detailed information about a specific story.

    Args:
        story_id: The Hacker News story ID
        include_comments: Whether to include comments (default: True)
        comment_depth: How deep to fetch nested comments, 1-10 (default: 3)
        max_comments: Max comments per level, 1-50 (default: 20)
    """
    # Clamp values to valid ranges
    comment_depth = min(max(1, comment_depth), 10)
    max_comments = min(max(1, max_comments), 50)

    async with HNClient() as client:
        if include_comments:
            story = await client.get_story_info(
                story_id,
                comment_depth=comment_depth,
                num_comments=max_comments,
            )
        else:
            # Fetch without comments - depth 0 means no comment processing
            story = await client.get_story_info(story_id, comment_depth=0)

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
    description="Get cache and rate limiter statistics for debugging and monitoring",
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def cache_stats() -> str:
    """Get current cache and rate limiter statistics."""
    result = {
        "cache": get_cache().stats(),
        "rate_limiter": await get_rate_limiter().stats(),
    }
    return json.dumps(result, indent=2)


# HN Culture Glossary (inspired by karanb192/hn-mcp's hn_explain tool)
HN_GLOSSARY: dict[str, dict[str, str]] = {
    "karma": {
        "definition": "Points accumulated from upvotes on your submissions and comments.",
        "context": "Higher karma indicates community trust. Some features require minimum karma.",
    },
    "flagged": {
        "definition": "Content marked by users as inappropriate, off-topic, or spam.",
        "context": "Flagged posts may be hidden or penalized in rankings.",
    },
    "dead": {
        "definition": "Content killed by moderators or auto-detected as low quality.",
        "context": "Dead posts are invisible unless 'showdead' is enabled in settings.",
    },
    "dupe": {
        "definition": "Duplicate submission of content already posted.",
        "context": "Dupes are typically merged or removed. HN has a 1-year lookback.",
    },
    "show_hn": {
        "definition": "Prefix for sharing something you made with the community.",
        "context": "Reserved for original work. Format: 'Show HN: [Title]'",
    },
    "ask_hn": {
        "definition": "Prefix for asking questions to the HN community.",
        "context": "Great for advice, opinions, or open-ended discussions.",
    },
    "tell_hn": {
        "definition": "Prefix for sharing information or announcements.",
        "context": "Less common than Ask/Show. Used for community PSAs.",
    },
    "pg": {
        "definition": "Paul Graham, co-founder of Y Combinator and creator of HN.",
        "context": "His username is 'pg'. His essays are legendary in the community.",
    },
    "dang": {
        "definition": "Daniel Gackle, lead moderator of Hacker News since 2014.",
        "context": "Known for thoughtful moderation and 'Please don't' reminders.",
    },
    "yc": {
        "definition": "Y Combinator, the startup accelerator that runs HN.",
        "context": "YC-funded startups often get attention on HN.",
    },
    "hn_guidelines": {
        "definition": "Official rules: no flamewars, be civil, assume good faith.",
        "context": "See https://news.ycombinator.com/newsguidelines.html",
    },
    "hellban": {
        "definition": "User's posts appear normal to them but invisible to others.",
        "context": "Applied to persistent rule violators. Also called 'shadowban'.",
    },
    "vouching": {
        "definition": "High-karma users can 'vouch' for dead/flagged content to restore it.",
        "context": "Click 'vouch' on dead comments you believe are legitimate.",
    },
    "topcolor": {
        "definition": "Orange bar at top that changes color at high karma (≈500+).",
        "context": "A vanity feature. Deeper orange = higher karma.",
    },
    "front_page": {
        "definition": "The main HN page showing ~30 top-ranked stories.",
        "context": "Stories are ranked by points, time, and engagement.",
    },
    "flame_war": {
        "definition": "Heated, unproductive argument thread.",
        "context": "Moderators may detach or kill flame war subtrees.",
    },
    "detached": {
        "definition": "Comment thread separated from parent discussion.",
        "context": "Done by mods when threads go off-topic.",
    },
}


def explain_hn_term(term: str) -> dict[str, str | list[str]]:
    """
    Get explanation of a Hacker News term or concept.

    Args:
        term: The HN term to explain (e.g., 'karma', 'Show HN', 'dang')

    Returns:
        Dict with definition, context, and related terms
    """
    # Normalize the term
    normalized = term.lower().strip().replace(" ", "_").replace("-", "_")

    # Handle common variations
    variations = {
        "show": "show_hn",
        "ask": "ask_hn",
        "tell": "tell_hn",
        "shadow_ban": "hellban",
        "shadowban": "hellban",
        "shadowbanned": "hellban",
        "shadow_banned": "hellban",
        "guidelines": "hn_guidelines",
        "rules": "hn_guidelines",
        "paul_graham": "pg",
        "daniel_gackle": "dang",
        "y_combinator": "yc",
        "ycombinator": "yc",
        "duplicate": "dupe",
        "duped": "dupe",
        "top_color": "topcolor",
        "flamewar": "flame_war",
        "flames": "flame_war",
        "frontpage": "front_page",
        "homepage": "front_page",
        "vouch": "vouching",
        "vouched": "vouching",
        "killed": "dead",
        "kill": "dead",
        "flag": "flagged",
        "flags": "flagged",
    }
    normalized = variations.get(normalized, normalized)

    if normalized in HN_GLOSSARY:
        entry = HN_GLOSSARY[normalized]
        return {
            "term": term,
            "normalized": normalized,
            "definition": entry["definition"],
            "context": entry["context"],
        }
    else:
        # Return list of available terms
        available = sorted(HN_GLOSSARY.keys())
        return {
            "term": term,
            "error": f"Unknown term: '{term}'",
            "available_terms": available,
            "hint": "Try one of the available terms, or search HN for more context.",
        }


@mcp.tool(
    name="hn_explain",
    description=(
        "Explain Hacker News terminology, culture, and conventions. "
        "Use this to understand HN-specific terms like 'karma', 'flagged', "
        "'Show HN', 'dang', 'hellban', etc."
    ),
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def hn_explain(term: str) -> str:
    """
    Get explanation of a Hacker News term or concept.

    Args:
        term: The HN term to explain (e.g., 'karma', 'Show HN', 'dang')

    Returns:
        JSON with definition, context, and related terms
    """
    result = explain_hn_term(term)
    return json.dumps(result, indent=2)


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
    """Run the MCP-HN server.

    Supports multiple transports via environment variables or CLI:
    - STDIO (default): For Claude Desktop, Cursor, etc.
    - HTTP: For web clients via `--transport http --port 8080`
    - SSE: For Server-Sent Events via `--transport sse`
    - Streamable HTTP: For interactive via `--transport streamable-http`

    Examples:
        # Default stdio transport
        hn-mcp

        # HTTP server on port 8080
        fastmcp run src/hn_mcp/server.py --transport http --port 8080

        # Or via uvicorn directly
        uvicorn hn_mcp.server:mcp.asgi_app --host 0.0.0.0 --port 8080
    """
    mcp.run()


# ASGI app for HTTP/SSE transport (uvicorn, hypercorn, etc.)
# Usage: uvicorn hn_mcp.server:asgi_app --host 0.0.0.0 --port 8080
asgi_app = mcp.http_app()


if __name__ == "__main__":
    main()
