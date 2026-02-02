"""
End-to-end tests for hn-mcp.

These tests hit the real Hacker News API and require network access.
Run with: pytest -m e2e

Following MCP best practices 2026:
- In-process testing with FastMCP Client (no subprocess overhead)
- Real API validation
- Timeout protection
"""

import json
from typing import Any

import pytest
from fastmcp import Client

from hn_mcp import mcp


def extract_json(result: Any) -> Any:
    """Extract JSON from FastMCP CallToolResult or ReadResourceResult."""
    # CallToolResult has .content list, ReadResourceResult might be different
    if hasattr(result, "content"):
        content = result.content
        if isinstance(content, list) and len(content) > 0:
            text = content[0].text if hasattr(content[0], "text") else str(content[0])
            return json.loads(text)
    # Fallback for other structures
    if hasattr(result, "text"):
        return json.loads(result.text)
    if isinstance(result, list) and len(result) > 0:
        return json.loads(result[0].text if hasattr(result[0], "text") else str(result[0]))
    raise ValueError(f"Cannot extract JSON from {type(result)}: {result}")


@pytest.mark.e2e
@pytest.mark.timeout(30)
class TestHNAPIIntegration:
    """E2E tests that hit the real Hacker News API."""

    @pytest.mark.asyncio
    async def test_get_top_stories_live(self) -> None:
        """Test fetching real top stories from HN."""
        async with Client(mcp) as client:
            result = await client.call_tool("get_stories", {"story_type": "top", "num_stories": 5})
            data = extract_json(result)

            # Validate structure
            assert isinstance(data, list)
            assert len(data) == 5

            # Validate story fields
            story = data[0]
            assert "id" in story
            assert "title" in story
            assert "author" in story
            assert isinstance(story["id"], int)

    @pytest.mark.asyncio
    async def test_search_stories_live(self) -> None:
        """Test searching real stories on HN."""
        async with Client(mcp) as client:
            result = await client.call_tool(
                "search_stories",
                {"query": "python", "num_results": 3}
            )
            data = extract_json(result)
            assert isinstance(data, list)
            assert len(data) >= 1  # At least one result for "python"

            # Each result should have basic fields
            for story in data:
                assert "id" in story
                assert "title" in story

    @pytest.mark.asyncio
    async def test_get_story_info_live(self) -> None:
        """Test fetching a specific story (story ID 1 is the first HN post)."""
        async with Client(mcp) as client:
            result = await client.call_tool("get_story_info", {"story_id": 1})
            data = extract_json(result)
            assert data["id"] == 1
            assert "Y Combinator" in data.get("title", "")
            assert data.get("author") == "pg"

    @pytest.mark.asyncio
    async def test_get_user_info_live(self) -> None:
        """Test fetching a real user (pg - Paul Graham)."""
        async with Client(mcp) as client:
            result = await client.call_tool(
                "get_user_info",
                {"user_name": "pg", "num_stories": 3}
            )
            data = extract_json(result)
            assert data["username"] == "pg"
            assert data["karma"] > 100000  # pg has lots of karma
            assert "stories" in data

    @pytest.mark.asyncio
    async def test_cache_stats_live(self) -> None:
        """Test cache stats tool."""
        async with Client(mcp) as client:
            result = await client.call_tool("cache_stats", {})
            data = extract_json(result)
            assert "total_items" in data
            assert "hits" in data
            assert "misses" in data
            assert "hit_rate" in data


@pytest.mark.e2e
@pytest.mark.timeout(30)
class TestResourcesIntegration:
    """E2E tests for MCP Resources."""

    @pytest.mark.asyncio
    async def test_read_top_stories_resource(self) -> None:
        """Test reading hackernews://top resource."""
        async with Client(mcp) as client:
            result = await client.read_resource("hackernews://top")
            data = extract_json(result)
            assert isinstance(data, list)
            assert len(data) == 30  # Resources return 30 stories

    @pytest.mark.asyncio
    async def test_read_story_resource(self) -> None:
        """Test reading hackernews://story/1 resource."""
        async with Client(mcp) as client:
            result = await client.read_resource("hackernews://story/1")
            data = extract_json(result)
            assert data["id"] == 1
            assert "Y Combinator" in data.get("title", "")


@pytest.mark.e2e
@pytest.mark.timeout(60)
class TestArticleExtraction:
    """E2E tests for article content extraction."""

    @pytest.mark.asyncio
    async def test_fetch_article_content_live(self) -> None:
        """Test fetching real article content."""
        async with Client(mcp) as client:
            # Use a stable, well-structured page
            result = await client.call_tool(
                "fetch_article_content",
                {"url": "https://news.ycombinator.com/newsguidelines.html"}
            )
            data = extract_json(result)

            # Should have url, title, content
            assert "url" in data
            assert "title" in data or "content" in data

            # Content should be non-empty if extraction succeeded
            if "content" in data:
                assert len(data["content"]) > 100

    @pytest.mark.asyncio
    async def test_fetch_article_blocked_host(self) -> None:
        """Test that blocked hosts return an error."""
        async with Client(mcp) as client:
            result = await client.call_tool(
                "fetch_article_content",
                {"url": "http://169.254.169.254/latest/meta-data/"}
            )
            data = extract_json(result)
            assert "error" in data
            assert "Blocked host" in data["error"]


@pytest.mark.e2e
@pytest.mark.timeout(30)
class TestPromptsIntegration:
    """E2E tests for MCP Prompts."""

    @pytest.mark.asyncio
    async def test_summarize_hn_prompt(self) -> None:
        """Test the summarize_hn prompt fetches real data."""
        async with Client(mcp) as client:
            result = await client.get_prompt("summarize_hn", {})

            # Prompt should have messages
            assert len(result.messages) > 0

            # First message content should have story data
            content = result.messages[0].content
            assert isinstance(content, str) or hasattr(content, "text")

    @pytest.mark.asyncio
    async def test_analyze_discussion_prompt(self) -> None:
        """Test the analyze_discussion prompt with story ID 1."""
        async with Client(mcp) as client:
            result = await client.get_prompt("analyze_discussion", {"story_id": 1})

            assert len(result.messages) > 0
            content = result.messages[0].content
            # Should mention Y Combinator (story 1's title)
            text = content if isinstance(content, str) else str(content)
            assert "Y Combinator" in text or "story" in text.lower()
