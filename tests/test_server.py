"""Integration/E2E tests for hn_mcp.server module.

These tests verify the MCP server tools work with the real HN API.
Mark with @pytest.mark.e2e to skip in CI.
"""

import json

import pytest


class TestToolRegistration:
    """Tests for tool registration."""

    def test_mcp_server_exists(self) -> None:
        """Test mcp server can be imported."""
        from hn_mcp.server import mcp
        assert mcp is not None
        assert mcp.name == "hn-mcp"

    def test_main_entry_point(self) -> None:
        """Test main entry point is callable."""
        from hn_mcp import main
        assert callable(main)


class TestGetStories:
    """Tests for get_stories tool."""

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_get_top_stories(self) -> None:
        """Test fetching top stories from real API."""
        from hn_mcp.hn import HNClient

        async with HNClient() as client:
            stories = await client.get_stories("top", 5)

        assert isinstance(stories, list)
        assert len(stories) == 5
        # Check story structure
        for story in stories:
            assert "id" in story
            assert "author" in story

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_get_ask_hn_stories(self) -> None:
        """Test fetching Ask HN stories (backward compatible)."""
        from hn_mcp.hn import HNClient

        async with HNClient() as client:
            stories = await client.get_stories("ask_hn", 3)

        assert isinstance(stories, list)
        assert len(stories) <= 3

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_get_show_hn_stories(self) -> None:
        """Test fetching Show HN stories (backward compatible)."""
        from hn_mcp.hn import HNClient

        async with HNClient() as client:
            stories = await client.get_stories("show_hn", 3)

        assert isinstance(stories, list)


class TestSearchStories:
    """Tests for search_stories tool."""

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_search_stories(self) -> None:
        """Test searching stories."""
        from hn_mcp.hn import HNClient

        async with HNClient() as client:
            results = await client.search_stories("python", 5)

        assert isinstance(results, list)
        # Search should find Python-related stories
        assert len(results) > 0


class TestGetStoryInfo:
    """Tests for get_story_info tool."""

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_get_story_info(self) -> None:
        """Test getting story details."""
        from hn_mcp.hn import HNClient

        # HN story ID 1 - the first HN post
        async with HNClient() as client:
            story = await client.get_story_info(1)

        assert isinstance(story, dict)
        assert story["id"] == 1
        assert "author" in story


class TestGetUserInfo:
    """Tests for get_user_info tool."""

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_get_user_info(self) -> None:
        """Test getting user details."""
        from hn_mcp.hn import HNClient

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
        from hn_mcp.cache import get_cache

        stats = get_cache().stats()

        assert isinstance(stats, dict)
        assert "total_items" in stats
        assert "hits" in stats
        assert "misses" in stats
        assert "hit_rate" in stats


class TestHNExplain:
    """Tests for hn_explain tool."""

    def test_explain_known_term(self) -> None:
        """Test explaining a known HN term."""
        from hn_mcp.server import explain_hn_term

        data = explain_hn_term("karma")

        assert data["term"] == "karma"
        assert data["normalized"] == "karma"
        assert "definition" in data
        assert "context" in data
        assert "upvotes" in data["definition"].lower()

    def test_explain_with_alias(self) -> None:
        """Test term aliases work correctly."""
        from hn_mcp.server import explain_hn_term

        data = explain_hn_term("Show HN")

        assert data["normalized"] == "show_hn"
        assert "definition" in data

    def test_explain_shadowban_alias(self) -> None:
        """Test shadowban maps to hellban."""
        from hn_mcp.server import explain_hn_term

        data = explain_hn_term("shadowban")

        assert data["normalized"] == "hellban"
        assert "invisible" in data["definition"].lower()

    def test_explain_dang(self) -> None:
        """Test dang term returns moderator info."""
        from hn_mcp.server import explain_hn_term

        data = explain_hn_term("dang")

        assert data["normalized"] == "dang"
        assert "moderator" in data["definition"].lower() or "daniel" in data["definition"].lower()

    def test_explain_unknown_term(self) -> None:
        """Test unknown term returns list of available terms."""
        from hn_mcp.server import explain_hn_term

        data = explain_hn_term("notarealterm")

        assert "error" in data
        assert "available_terms" in data
        assert isinstance(data["available_terms"], list)
        assert "karma" in data["available_terms"]

    def test_explain_case_insensitive(self) -> None:
        """Test terms are case-insensitive."""
        from hn_mcp.server import explain_hn_term

        data = explain_hn_term("KARMA")

        assert data["normalized"] == "karma"
        assert "definition" in data

    def test_explain_all_glossary_terms(self) -> None:
        """Test all glossary terms have required fields."""
        from hn_mcp.server import HN_GLOSSARY

        for term, entry in HN_GLOSSARY.items():
            assert "definition" in entry, f"Missing definition for {term}"
            assert "context" in entry, f"Missing context for {term}"
            assert len(entry["definition"]) > 10, f"Definition too short for {term}"


class TestRateLimiter:
    """Tests for rate limiting module."""

    @pytest.mark.asyncio
    async def test_rate_limiter_basic(self) -> None:
        """Test rate limiter allows requests under limit."""
        from hn_mcp.rate_limit import RateLimiter, RateLimitConfig

        limiter = RateLimiter(config=RateLimitConfig(requests_per_minute=100))

        # Should allow immediate acquisition
        wait_time = await limiter.acquire()
        assert wait_time == 0.0

    @pytest.mark.asyncio
    async def test_rate_limiter_stats(self) -> None:
        """Test rate limiter stats."""
        from hn_mcp.rate_limit import RateLimiter, RateLimitConfig

        limiter = RateLimiter(config=RateLimitConfig(requests_per_minute=100))

        # Make a few requests
        await limiter.acquire()
        await limiter.acquire()
        await limiter.acquire()

        stats = await limiter.stats()

        assert stats["requests_in_window"] == 3
        assert stats["requests_per_minute_limit"] == 100
        assert "capacity_used_percent" in stats

    @pytest.mark.asyncio
    async def test_rate_limiter_reset(self) -> None:
        """Test rate limiter reset."""
        from hn_mcp.rate_limit import RateLimiter, RateLimitConfig

        limiter = RateLimiter(config=RateLimitConfig(requests_per_minute=100))

        await limiter.acquire()
        await limiter.acquire()

        assert (await limiter.stats())["requests_in_window"] == 2

        limiter.reset()
        assert (await limiter.stats())["requests_in_window"] == 0

    def test_global_rate_limiter(self) -> None:
        """Test global rate limiter singleton."""
        from hn_mcp.rate_limit import get_rate_limiter, configure_rate_limiter

        # Configure with custom limit
        limiter = configure_rate_limiter(requests_per_minute=500)
        assert limiter.config.requests_per_minute == 500

        # Get should return same instance
        same_limiter = get_rate_limiter()
        assert same_limiter is limiter
