"""Tests for the HN client."""

import pytest
from hn_mcp.hn import HNClient, VALID_STORY_TYPES


@pytest.fixture
async def client():
    """Create an async HN client."""
    async with HNClient() as c:
        yield c


class TestHNClient:
    """Test cases for HNClient."""

    @pytest.mark.asyncio
    async def test_get_stories_top(self, client: HNClient):
        """Test fetching top stories."""
        stories = await client.get_stories("top", 5)
        assert len(stories) <= 5
        assert all("id" in s for s in stories)

    @pytest.mark.asyncio
    async def test_get_stories_invalid_type(self, client: HNClient):
        """Test that invalid story type raises error."""
        from hn_mcp.hn import HNClientError
        
        with pytest.raises(HNClientError):
            await client.get_stories("invalid_type")

    @pytest.mark.asyncio
    async def test_search_stories(self, client: HNClient):
        """Test searching stories."""
        results = await client.search_stories("python", 5)
        assert len(results) <= 5

    @pytest.mark.asyncio
    async def test_valid_story_types(self):
        """Test all valid story types are covered."""
        # Backward compatible: ask_hn, show_hn plus aliases ask, show
        expected = ["top", "new", "best", "ask_hn", "show_hn", "job", "ask", "show"]
        for t in expected:
            assert t in VALID_STORY_TYPES
