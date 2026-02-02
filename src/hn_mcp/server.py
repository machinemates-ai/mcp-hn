"""
HN-MCP Server - FastMCP 3.0 Implementation.

A comprehensive MCP server for Hacker News with:
- Tools: Search, get stories, get user info, fetch article content
- Resources: hackernews:// URIs for top/new/best/ask/show/job stories
- Prompts: Templates for common HN analysis tasks
- Caching: LRU cache with adaptive TTLs
- Async: Full async/await with httpx
"""

import json

from fastmcp import FastMCP

from hn_mcp.cache import get_cache
from hn_mcp.client import HNClient
from hn_mcp.content import ContentExtractionError, fetch_article_content

# Create FastMCP server
mcp = FastMCP(
    name="hn-mcp",
    version="1.0.0",
    instructions="""
    HN-MCP provides access to Hacker News via MCP.
    
    Available capabilities:
    - Tools: Search stories, get story details, get user info, fetch article content
    - Resources: Access story feeds via hackernews:// URIs
    - Prompts: Templates for news analysis and summarization
    
    For browsing stories, use the hackernews:// resources.
    For specific queries, use the search_stories tool.
    For article content, use fetch_article_content tool.
    """,
)


# =============================================================================
# TOOLS - Interactive operations
# =============================================================================

@mcp.tool(
    name="get_stories",
    description="Get stories from Hacker News by type (top, new, best, ask, show, job)",
)
async def get_stories(
    story_type: str = "top",
    num_stories: int = 10,
) -> str:
    """
    Fetch Hacker News stories by type.
    
    Args:
        story_type: Type of stories - 'top', 'new', 'best', 'ask', 'show', 'job'
        num_stories: Number of stories to return (1-50, default: 10)
    """
    num_stories = min(max(1, num_stories), 50)  # Clamp to 1-50
    
    async with HNClient() as client:
        stories = await client.get_stories(story_type, num_stories)
    
    return json.dumps(stories, indent=2)


@mcp.tool(
    name="search_stories",
    description="Search Hacker News stories. Use simple queries (< 5 words) for best results.",
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
        num_results: Number of results (1-50, default: 10)
        search_by_date: If True, sort by date; else by relevance
    """
    num_results = min(max(1, num_results), 50)
    
    async with HNClient() as client:
        results = await client.search_stories(query, num_results, search_by_date)
    
    return json.dumps(results, indent=2)


@mcp.tool(
    name="get_story",
    description="Get detailed story info including comments",
)
async def get_story(
    story_id: int,
    include_comments: bool = True,
    comment_depth: int = 2,
    num_comments: int = 10,
) -> str:
    """
    Get detailed information about a specific story.
    
    Args:
        story_id: The Hacker News story ID
        include_comments: Whether to include comments (default: True)
        comment_depth: Depth of nested comments to fetch (1-5, default: 2)
        num_comments: Max comments per level (1-30, default: 10)
    """
    comment_depth = min(max(1, comment_depth), 5)
    num_comments = min(max(1, num_comments), 30)
    
    async with HNClient() as client:
        story = await client.get_story(story_id, include_comments, comment_depth, num_comments)
    
    return json.dumps(story, indent=2)


@mcp.tool(
    name="get_user",
    description="Get Hacker News user info and their recent stories",
)
async def get_user(
    username: str,
    include_stories: bool = True,
    num_stories: int = 10,
) -> str:
    """
    Get information about a Hacker News user.
    
    Args:
        username: The HN username
        include_stories: Include user's recent stories (default: True)
        num_stories: Number of stories to include (1-30, default: 10)
    """
    num_stories = min(max(1, num_stories), 30)
    
    async with HNClient() as client:
        user = await client.get_user(username, include_stories, num_stories)
    
    return json.dumps(user, indent=2)


@mcp.tool(
    name="fetch_article_content",
    description="Fetch and extract article content as Markdown from a story's URL",
)
async def tool_fetch_article_content(url: str) -> str:
    """
    Fetch article content and convert to Markdown.
    
    Args:
        url: The article URL to fetch
    
    Returns:
        Markdown content of the article
    """
    try:
        result = await fetch_article_content(url)
        return json.dumps(result, indent=2)
    except ContentExtractionError as e:
        return json.dumps({"error": str(e)})


@mcp.tool(
    name="cache_stats",
    description="Get cache statistics for debugging and monitoring",
)
async def cache_stats() -> str:
    """Get current cache statistics."""
    stats = get_cache().stats()
    return json.dumps(stats, indent=2)


# =============================================================================
# RESOURCES - Read-only data access via URIs
# Like paabloLC/mcp-hacker-news hackernews:// patterns
# =============================================================================

@mcp.resource(
    uri="hackernews://top",
    name="Top Stories",
    description="Top stories currently on Hacker News front page",
    mime_type="application/json",
    tags={"stories", "top"},
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
    tags={"stories", "new"},
)
async def resource_new_stories() -> str:
    """Get newest stories."""
    async with HNClient() as client:
        stories = await client.get_stories("new", 30)
    return json.dumps(stories, indent=2)


@mcp.resource(
    uri="hackernews://best",
    name="Best Stories",
    description="Best stories on Hacker News (highest voted)",
    mime_type="application/json",
    tags={"stories", "best"},
)
async def resource_best_stories() -> str:
    """Get best stories."""
    async with HNClient() as client:
        stories = await client.get_stories("best", 30)
    return json.dumps(stories, indent=2)


@mcp.resource(
    uri="hackernews://ask",
    name="Ask HN",
    description="Ask HN posts - questions from the community",
    mime_type="application/json",
    tags={"stories", "ask"},
)
async def resource_ask_stories() -> str:
    """Get Ask HN posts."""
    async with HNClient() as client:
        stories = await client.get_stories("ask", 30)
    return json.dumps(stories, indent=2)


@mcp.resource(
    uri="hackernews://show",
    name="Show HN",
    description="Show HN posts - projects shared by the community",
    mime_type="application/json",
    tags={"stories", "show"},
)
async def resource_show_stories() -> str:
    """Get Show HN posts."""
    async with HNClient() as client:
        stories = await client.get_stories("show", 30)
    return json.dumps(stories, indent=2)


@mcp.resource(
    uri="hackernews://jobs",
    name="Jobs",
    description="Job postings on Hacker News",
    mime_type="application/json",
    tags={"stories", "jobs"},
)
async def resource_job_stories() -> str:
    """Get job postings."""
    async with HNClient() as client:
        stories = await client.get_stories("job", 30)
    return json.dumps(stories, indent=2)


# Resource template for individual stories
@mcp.resource(
    uri="hackernews://story/{story_id}",
    name="Story Details",
    description="Get detailed information about a specific story including comments",
    mime_type="application/json",
)
async def resource_story_detail(story_id: str) -> str:
    """Get story details by ID."""
    async with HNClient() as client:
        story = await client.get_story(int(story_id), include_comments=True)
    return json.dumps(story, indent=2)


# Resource template for user profiles
@mcp.resource(
    uri="hackernews://user/{username}",
    name="User Profile",
    description="Get user profile and recent submissions",
    mime_type="application/json",
)
async def resource_user_profile(username: str) -> str:
    """Get user profile."""
    async with HNClient() as client:
        user = await client.get_user(username, include_stories=True)
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
        f"- [{s.get('title', 'Untitled')}]({s.get('url', '')}) by {s.get('author', 'unknown')} ({s.get('points', 0)} points)"
        for s in stories
    )
    
    return f"""Summarize these top Hacker News stories, identifying key themes and notable discussions:

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
        story = await client.get_story(story_id, include_comments=True, comment_depth=3, num_comments=20)
    
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


@mcp.prompt(
    name="compare_coverage",
    description="Compare how HN community reacts to a topic vs mainstream coverage",
)
async def prompt_compare_coverage(query: str) -> str:
    """Generate a prompt for comparing HN coverage to mainstream."""
    async with HNClient() as client:
        results = await client.search_stories(query, num_results=10)
    
    stories_text = "\n".join(
        f"- {s.get('title', 'Untitled')} ({s.get('points', 0)} points, {s.get('num_comments', 0)} comments)"
        for s in results
    )
    
    return f"""Based on these Hacker News stories about "{query}":

{stories_text}

Analyze:
1. How is the HN community discussing this topic?
2. What unique perspectives does the tech community bring?
3. Are there any contrarian viewpoints?
4. What technical details are being highlighted?"""


# =============================================================================
# Entry point
# =============================================================================

def main() -> None:
    """Run the HN-MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
