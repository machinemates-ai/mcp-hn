"""
Unit tests for mcp_hn.hn module (HN Client).
"""

import pytest

from mcp_hn.hn import (
    DEFAULT_NUM_STORIES,
    HNClient,
    HNClientError,
    VALID_STORY_TYPES,
)


class TestHNClientStoryTypes:
    """Tests for story type validation."""

    def test_valid_story_types(self) -> None:
        """Check all expected story types are valid."""
        expected = ["top", "new", "best", "ask_hn", "show_hn", "job", "ask", "show"]
        for story_type in expected:
            assert story_type in VALID_STORY_TYPES

    def test_story_type_aliases(self) -> None:
        """Verify ask/show are aliases for ask_hn/show_hn."""
        assert "ask" in VALID_STORY_TYPES
        assert "ask_hn" in VALID_STORY_TYPES
        assert "show" in VALID_STORY_TYPES
        assert "show_hn" in VALID_STORY_TYPES


class TestHNClient:
    """Tests for HNClient class."""

    @pytest.fixture
    def client(self) -> HNClient:
        """Create HN client instance."""
        return HNClient()

    def test_default_values(self) -> None:
        """Test default configuration values."""
        assert DEFAULT_NUM_STORIES == 10

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        """Test client works as async context manager."""
        async with HNClient() as client:
            assert client._client is not None
        # After exit, client should be closed
        assert client._client is None

    @pytest.mark.asyncio
    async def test_get_stories_invalid_type(self, client: HNClient) -> None:
        """Test get_stories with invalid story type raises error."""
        async with client:
            with pytest.raises(HNClientError) as exc_info:
                await client.get_stories("invalid_type")
            assert "story_type must be one of" in str(exc_info.value)


class TestStoryFormatting:
    """Tests for story and comment formatting."""

    @pytest.fixture
    def client(self) -> HNClient:
        return HNClient()

    def test_format_story_minimal(self, client: HNClient) -> None:
        """Test formatting story with minimal fields."""
        raw = {"objectID": "123", "author": "user"}
        formatted = client._format_story(raw)
        assert formatted["id"] == 123
        assert formatted["author"] == "user"

    def test_format_story_with_all_fields(self, client: HNClient) -> None:
        """Test formatting story with all fields."""
        raw = {
            "story_id": 456,
            "author": "user",
            "title": "Test Title",
            "url": "https://example.com",
            "points": 100,
            "created_at": "2024-01-01T00:00:00Z",
            "num_comments": 50,
            "story_text": "Some text",
        }
        formatted = client._format_story(raw)
        assert formatted["id"] == 456
        assert formatted["title"] == "Test Title"
        assert formatted["url"] == "https://example.com"
        assert formatted["points"] == 100
        assert formatted["num_comments"] == 50
        assert formatted["text"] == "Some text"

    def test_format_comments_empty(self, client: HNClient) -> None:
        """Test formatting empty comments list."""
        result = client._format_comments([], depth=2, max_per_level=10)
        assert result == []

    def test_format_comments_depth_limit(self, client: HNClient) -> None:
        """Test that depth=0 returns empty list."""
        comments = [{"author": "user", "text": "comment", "children": []}]
        result = client._format_comments(comments, depth=0, max_per_level=10)
        assert result == []

    def test_format_comments_with_children(self, client: HNClient) -> None:
        """Test formatting nested comments."""
        comments = [
            {
                "author": "user1",
                "text": "parent",
                "children": [
                    {"author": "user2", "text": "child", "children": []},
                ],
            }
        ]
        result = client._format_comments(comments, depth=2, max_per_level=10)
        assert len(result) == 1
        assert result[0]["author"] == "user1"
        assert result[0]["text"] == "parent"
        assert len(result[0]["comments"]) == 1
        assert result[0]["comments"][0]["author"] == "user2"

    def test_format_comments_max_per_level(self, client: HNClient) -> None:
        """Test max comments per level limit."""
        comments = [
            {"author": f"user{i}", "text": f"comment{i}", "children": []}
            for i in range(5)
        ]
        result = client._format_comments(comments, depth=1, max_per_level=2)
        assert len(result) == 2
