"""
Integration/E2E tests for mcp_hn.server module.

These tests verify the MCP server tools work with the real HN API.
Mark with @pytest.mark.integration to skip in CI.
"""

import json

import pytest


class TestToolRegistration:
    """Tests for tool registration matching original mcp-hn."""

    def test_mcp_server_exists(self) -> None:
        """Test mcp server can be imported."""
        from mcp_hn.server import mcp
        assert mcp is not None
        assert mcp.name == "hn"

    def test_main_entry_point(self) -> None:
        """Test main entry point is callable."""
        from mcp_hn import main
        assert callable(main)


class TestGetStories:
    """Tests for get_stories tool."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_top_stories(self) -> None:
        """Test fetching top stories from real API."""
        from mcp_hn.hn import HNClient

        async with HNClient() as client:
            stories = await client.get_stories("top", 5)

        assert isinstance(stories, list)
        assert len(stories) == 5
        # Check story structure
        for story in stories:
            assert "id" in story
            assert "author" in story

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_ask_hn_stories(self) -> None:
        """Test fetching Ask HN stories (backward compatible)."""
        from mcp_hn.hn import HNClient

        async with HNClient() as client:
            stories = await client.get_stories("ask_hn", 3)

        assert isinstance(stories, list)
        assert len(stories) <= 3

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_show_hn_stories(self) -> None:
        """Test fetching Show HN stories (backward compatible)."""
        from mcp_hn.hn import HNClient

        async with HNClient() as client:
            stories = await client.get_stories("show_hn", 3)

        assert isinstance(stories, list)


class TestSearchStories:
    """Tests for search_stories tool."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_search_stories(self) -> None:
        """Test searching stories."""
        from mcp_hn.hn import HNClient

        async with HNClient() as client:
            results = await client.search_stories("python", 5)

        assert isinstance(results, list)
        # Search should find Python-related stories
        assert len(results) > 0


class TestGetStoryInfo:
    """Tests for get_story_info tool."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_story_info(self) -> None:
        """Test getting story details."""
        from mcp_hn.hn import HNClient

        # HN story ID 1 - the first HN post
        async with HNClient() as client:
            story = await client.get_story_info(1)

        assert isinstance(story, dict)
        assert story["id"] == 1
        assert "author" in story


class TestGetUserInfo:
    """Tests for get_user_info tool."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_user_info(self) -> None:
        """Test getting user details."""
        from mcp_hn.hn import HNClient

        # pg is HN founder
        async with HNClient() as client:
            user = await client.get_user_info("pg", 3)

        assert isinstance(user, dict)
        assert user["username"] == "pg"
        assert "karma" in user
        assert "stories" in user


class TestCacheStats:
    """Tests for cache_stats tool."""

    @pytest.mark.asyncio
    async def test_cache_stats(self) -> None:
        """Test cache stats tool returns valid data."""
        from mcp_hn.cache import get_cache

        stats = get_cache().stats()

        assert isinstance(stats, dict)
        assert "total_items" in stats
        assert "hits" in stats
        assert "misses" in stats
        assert "hit_rate" in stats
