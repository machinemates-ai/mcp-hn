"""
Async Hacker News API Client.

Supports both the Algolia API (for search) and the official Firebase API.
Uses httpx for async HTTP requests.

API References:
- Algolia: http://hn.algolia.com/api/v1
- Firebase: https://hacker-news.firebaseio.com/v0/

Backward compatible with erithwik/mcp-hn function signatures.
"""

from typing import Any
from urllib.parse import quote

import httpx

from hn_mcp.cache import cached
from hn_mcp.rate_limit import get_rate_limiter

# API Base URLs
ALGOLIA_BASE = "https://hn.algolia.com/api/v1"
FIREBASE_BASE = "https://hacker-news.firebaseio.com/v0"

# Defaults (match original mcp-hn)
DEFAULT_NUM_STORIES = 10
DEFAULT_NUM_COMMENTS = 10
DEFAULT_COMMENT_DEPTH = 2
DEFAULT_TIMEOUT = 30.0

# Story type mappings - MUST match original: top, new, ask_hn, show_hn
# Plus extensions: best, job
STORY_TYPE_PARAMS: dict[str, dict[str, str]] = {
    "top": {"endpoint": "search", "tags": "front_page"},
    "new": {"endpoint": "search_by_date", "tags": "story"},
    "best": {"endpoint": "search", "tags": "front_page"},  # Alias for top
    "ask_hn": {"endpoint": "search", "tags": "ask_hn"},
    "show_hn": {"endpoint": "search", "tags": "show_hn"},
    "job": {"endpoint": "search", "tags": "job"},
    # Aliases for new format
    "ask": {"endpoint": "search", "tags": "ask_hn"},
    "show": {"endpoint": "search", "tags": "show_hn"},
}

VALID_STORY_TYPES = list(STORY_TYPE_PARAMS.keys())


class HNClientError(Exception):
    """Base exception for HN client errors."""

    pass


class HNClient:
    """
    Async Hacker News API client with caching support.

    Uses both Algolia API (fast, search-optimized) and Firebase API (official).
    """

    def __init__(self, timeout: float = DEFAULT_TIMEOUT) -> None:
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "HNClient":
        self._client = httpx.AsyncClient(
            timeout=self._timeout,
            headers={"User-Agent": "mcp-hn/1.0"},
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                headers={"User-Agent": "mcp-hn/1.0"},
                follow_redirects=True,
            )
        return self._client

    async def _rate_limited_get(self, url: str) -> httpx.Response:
        """Make a rate-limited GET request.

        Waits if necessary to respect the global rate limit before making the request.
        """
        rate_limiter = get_rate_limiter()
        await rate_limiter.wait_and_acquire()
        return await self.client.get(url)

    # =========================================================================
    # Algolia API Methods (fast, search-optimized)
    # =========================================================================

    @cached("stories_list")
    async def get_stories(
        self,
        story_type: str = "top",
        num_stories: int = DEFAULT_NUM_STORIES,
    ) -> list[dict[str, Any]]:
        """
        Get stories from Hacker News.

        Args:
            story_type: One of 'top', 'new', 'best', 'ask_hn', 'show_hn', 'job'
                       (also accepts 'ask', 'show' as aliases)
            num_stories: Number of stories to fetch (default: 10)

        Returns:
            List of story dictionaries with id, title, url, author, points, etc.
        """
        story_type = story_type.lower().strip()
        if story_type not in VALID_STORY_TYPES:
            raise HNClientError(
                f"story_type must be one of: {', '.join(VALID_STORY_TYPES)}"
            )

        params = STORY_TYPE_PARAMS[story_type]
        url = (
            f"{ALGOLIA_BASE}/{params['endpoint']}"
            f"?tags={params['tags']}&hitsPerPage={num_stories}"
        )

        response = await self._rate_limited_get(url)
        response.raise_for_status()
        data = response.json()

        return [self._format_story(hit) for hit in data.get("hits", [])]

    @cached("search_results")
    async def search_stories(
        self,
        query: str,
        num_results: int = DEFAULT_NUM_STORIES,
        search_by_date: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Search Hacker News stories.

        Args:
            query: Search query
            num_results: Number of results to return (default: 10)
            search_by_date: If True, sort by date; else by relevance/points

        Returns:
            List of matching story dictionaries
        """
        endpoint = "search_by_date" if search_by_date else "search"
        # URL-encode query to handle special chars like &, +, #, =
        encoded_query = quote(query, safe="")
        url = (
            f"{ALGOLIA_BASE}/{endpoint}"
            f"?query={encoded_query}&hitsPerPage={num_results}&tags=story"
        )

        response = await self._rate_limited_get(url)
        response.raise_for_status()
        data = response.json()

        return [self._format_story(hit) for hit in data.get("hits", [])]

    @cached("story_detail")
    async def get_story_info(
        self,
        story_id: int,
        comment_depth: int = DEFAULT_COMMENT_DEPTH,
        num_comments: int = DEFAULT_NUM_COMMENTS,
    ) -> dict[str, Any]:
        """
        Get detailed story info including comments.

        Matches original mcp-hn signature: get_story_info(story_id)

        Args:
            story_id: The HN story ID
            comment_depth: How deep to fetch nested comments (default: 2)
            num_comments: Max comments per level (default: 10)

        Returns:
            Story dictionary with id, title, url, author, points, and comments
        """
        url = f"{ALGOLIA_BASE}/items/{story_id}"
        response = await self._rate_limited_get(url)
        response.raise_for_status()
        data = response.json()

        story = self._format_story(data)

        if "children" in data and data["children"]:
            story["comments"] = self._format_comments(
                data["children"],
                depth=comment_depth,
                max_per_level=num_comments,
            )

        return story

    @cached("user_info")
    async def get_user_info(
        self,
        user_name: str,
        num_stories: int = DEFAULT_NUM_STORIES,
    ) -> dict[str, Any]:
        """
        Get user info from Hacker News.

        Matches original mcp-hn signature: get_user_info(user_name, num_stories)

        Args:
            user_name: The HN username
            num_stories: Number of stories to include (default: 10)

        Returns:
            User dictionary with id, karma, about, created_at, and stories
        """
        url = f"{ALGOLIA_BASE}/users/{user_name}"
        response = await self._rate_limited_get(url)
        response.raise_for_status()
        user_data = response.json()

        result = {
            "id": user_data.get("username"),
            "username": user_data.get("username"),
            "karma": user_data.get("karma"),
            "about": user_data.get("about"),
            "created_at": user_data.get("created_at"),
        }

        # Fetch user's stories
        stories_url = (
            f"{ALGOLIA_BASE}/search"
            f"?tags=author_{user_name},story&hitsPerPage={num_stories}"
        )
        stories_response = await self._rate_limited_get(stories_url)
        stories_response.raise_for_status()
        stories_data = stories_response.json()
        result["stories"] = [
            self._format_story(hit) for hit in stories_data.get("hits", [])
        ]

        return result

    # =========================================================================
    # Firebase API Methods (official, real-time)
    # =========================================================================

    @cached("stories_list")
    async def get_story_ids_firebase(
        self,
        story_type: str = "top",
        limit: int = DEFAULT_NUM_STORIES,
    ) -> list[int]:
        """Get story IDs from the official Firebase API."""
        type_map = {
            "top": "topstories",
            "new": "newstories",
            "best": "beststories",
            "ask": "askstories",
            "ask_hn": "askstories",
            "show": "showstories",
            "show_hn": "showstories",
            "job": "jobstories",
        }

        endpoint = type_map.get(story_type.lower(), "topstories")
        url = f"{FIREBASE_BASE}/{endpoint}.json"

        response = await self._rate_limited_get(url)
        response.raise_for_status()
        ids = response.json() or []

        return ids[:limit]

    @cached("story_detail")
    async def get_item_firebase(self, item_id: int) -> dict[str, Any] | None:
        """Get a single item from Firebase API."""
        url = f"{FIREBASE_BASE}/item/{item_id}.json"
        response = await self._rate_limited_get(url)
        response.raise_for_status()
        return response.json()

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _format_story(self, story: dict[str, Any]) -> dict[str, Any]:
        """Format a story from Algolia API response."""
        # Use story_id for consistency with original mcp-hn
        story_id = story.get("story_id") or story.get("objectID")
        result: dict[str, Any] = {
            "id": int(story_id) if story_id else None,
            "author": story.get("author"),
        }

        if story.get("title"):
            result["title"] = story["title"]
        if story.get("url"):
            result["url"] = story["url"]
        if story.get("points") is not None:
            result["points"] = story["points"]
        if story.get("created_at"):
            result["created_at"] = story["created_at"]
        if story.get("num_comments") is not None:
            result["num_comments"] = story["num_comments"]
        if story.get("story_text"):
            result["text"] = story["story_text"]

        return result

    def _format_comments(
        self,
        comments: list[dict[str, Any]],
        depth: int = DEFAULT_COMMENT_DEPTH,
        max_per_level: int = DEFAULT_NUM_COMMENTS,
    ) -> list[dict[str, Any]]:
        """Recursively format comments with depth limit."""
        if not comments or depth <= 0:
            return []

        result = []
        for comment in comments[:max_per_level]:
            formatted: dict[str, Any] = {
                "author": comment.get("author"),
                "text": comment.get("text", ""),
            }

            if depth > 1 and comment.get("children"):
                formatted["comments"] = self._format_comments(
                    comment["children"],
                    depth=depth - 1,
                    max_per_level=max_per_level,
                )

            result.append(formatted)

        return result


# Singleton client instance
_global_client: HNClient | None = None


async def get_client() -> HNClient:
    """Get or create the global HN client."""
    global _global_client
    if _global_client is None:
        _global_client = HNClient()
        await _global_client.__aenter__()
    return _global_client
