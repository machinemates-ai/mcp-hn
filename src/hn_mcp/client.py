"""
Async Hacker News API Client.

Supports both the Algolia API (for search) and the official Firebase API.
Uses httpx for async HTTP requests.

API References:
- Algolia: http://hn.algolia.com/api/v1
- Firebase: https://hacker-news.firebaseio.com/v0/
"""

from typing import Any

import httpx

from hn_mcp.cache import cached

# API Base URLs
ALGOLIA_BASE = "https://hn.algolia.com/api/v1"
FIREBASE_BASE = "https://hacker-news.firebaseio.com/v0"

# Defaults
DEFAULT_NUM_STORIES = 10
DEFAULT_NUM_COMMENTS = 10
DEFAULT_COMMENT_DEPTH = 2
DEFAULT_TIMEOUT = 30.0

# Story type mappings for Algolia API
STORY_TYPE_PARAMS = {
    "top": {"endpoint": "search", "tags": "front_page"},
    "new": {"endpoint": "search_by_date", "tags": "story"},
    "best": {"endpoint": "search", "tags": "front_page"},  # Same as top for Algolia
    "ask": {"endpoint": "search", "tags": "ask_hn"},
    "show": {"endpoint": "search", "tags": "show_hn"},
    "job": {"endpoint": "search", "tags": "job"},
}

# Valid story types
VALID_STORY_TYPES = list(STORY_TYPE_PARAMS.keys())


class HNClientError(Exception):
    """Base exception for HN client errors."""
    pass


class HNClient:
    """
    Async Hacker News API client with caching support.
    
    Uses both Algolia API (fast, search-optimized) and Firebase API (official, real-time).
    """
    
    def __init__(self, timeout: float = DEFAULT_TIMEOUT) -> None:
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None
    
    async def __aenter__(self) -> "HNClient":
        self._client = httpx.AsyncClient(
            timeout=self._timeout,
            headers={"User-Agent": "hn-mcp/1.0"},
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
            # Create a client for one-shot use
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                headers={"User-Agent": "hn-mcp/1.0"},
                follow_redirects=True,
            )
        return self._client
    
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
            story_type: One of 'top', 'new', 'best', 'ask', 'show', 'job'
            num_stories: Number of stories to fetch (default: 10)
        
        Returns:
            List of story dictionaries with id, title, url, author, points, etc.
        """
        story_type = story_type.lower().strip()
        if story_type not in VALID_STORY_TYPES:
            raise HNClientError(f"Invalid story_type: {story_type}. Must be one of {VALID_STORY_TYPES}")
        
        params = STORY_TYPE_PARAMS[story_type]
        url = f"{ALGOLIA_BASE}/{params['endpoint']}?tags={params['tags']}&hitsPerPage={num_stories}"
        
        response = await self.client.get(url)
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
        url = f"{ALGOLIA_BASE}/{endpoint}?query={query}&hitsPerPage={num_results}&tags=story"
        
        response = await self.client.get(url)
        response.raise_for_status()
        data = response.json()
        
        return [self._format_story(hit) for hit in data.get("hits", [])]
    
    @cached("story_detail")
    async def get_story(
        self,
        story_id: int,
        include_comments: bool = True,
        comment_depth: int = DEFAULT_COMMENT_DEPTH,
        num_comments: int = DEFAULT_NUM_COMMENTS,
    ) -> dict[str, Any]:
        """
        Get detailed story info including comments.
        
        Args:
            story_id: The HN story ID
            include_comments: Whether to include comments
            comment_depth: How deep to fetch nested comments (default: 2)
            num_comments: Max comments per level (default: 10)
        
        Returns:
            Story dictionary with id, title, url, author, points, and comments
        """
        url = f"{ALGOLIA_BASE}/items/{story_id}"
        response = await self.client.get(url)
        response.raise_for_status()
        data = response.json()
        
        story = self._format_story(data)
        
        if include_comments and "children" in data:
            story["comments"] = self._format_comments(
                data["children"], 
                depth=comment_depth,
                max_per_level=num_comments,
            )
            story["num_comments"] = len(data.get("children", []))
        
        return story
    
    @cached("user_info")
    async def get_user(
        self,
        username: str,
        include_stories: bool = True,
        num_stories: int = DEFAULT_NUM_STORIES,
    ) -> dict[str, Any]:
        """
        Get user info from Hacker News.
        
        Args:
            username: The HN username
            include_stories: Whether to include user's recent stories
            num_stories: Number of stories to include (default: 10)
        
        Returns:
            User dictionary with username, karma, about, created_at, and stories
        """
        url = f"{ALGOLIA_BASE}/users/{username}"
        response = await self.client.get(url)
        response.raise_for_status()
        user_data = response.json()
        
        result = {
            "username": user_data.get("username"),
            "karma": user_data.get("karma"),
            "about": user_data.get("about"),
            "created_at": user_data.get("created_at"),
        }
        
        if include_stories:
            stories_url = f"{ALGOLIA_BASE}/search?tags=author_{username},story&hitsPerPage={num_stories}"
            stories_response = await self.client.get(stories_url)
            stories_response.raise_for_status()
            stories_data = stories_response.json()
            result["stories"] = [self._format_story(hit) for hit in stories_data.get("hits", [])]
        
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
        """
        Get story IDs from the official Firebase API.
        
        Args:
            story_type: One of 'top', 'new', 'best', 'ask', 'show', 'job'
            limit: Number of story IDs to return
        
        Returns:
            List of story IDs
        """
        type_map = {
            "top": "topstories",
            "new": "newstories", 
            "best": "beststories",
            "ask": "askstories",
            "show": "showstories",
            "job": "jobstories",
        }
        
        endpoint = type_map.get(story_type.lower(), "topstories")
        url = f"{FIREBASE_BASE}/{endpoint}.json"
        
        response = await self.client.get(url)
        response.raise_for_status()
        ids = response.json() or []
        
        return ids[:limit]
    
    @cached("story_detail")
    async def get_item_firebase(self, item_id: int) -> dict[str, Any] | None:
        """
        Get a single item (story, comment, etc.) from Firebase API.
        
        Args:
            item_id: The HN item ID
        
        Returns:
            Item dictionary or None if not found
        """
        url = f"{FIREBASE_BASE}/item/{item_id}.json"
        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _format_story(self, story: dict[str, Any]) -> dict[str, Any]:
        """Format a story from Algolia API response."""
        result: dict[str, Any] = {
            "id": story.get("story_id") or story.get("objectID"),
        }
        
        if "title" in story and story["title"]:
            result["title"] = story["title"]
        if "url" in story and story["url"]:
            result["url"] = story["url"]
        if "author" in story:
            result["author"] = story["author"]
        if "points" in story:
            result["points"] = story["points"]
        if "created_at" in story:
            result["created_at"] = story["created_at"]
        if "num_comments" in story:
            result["num_comments"] = story["num_comments"]
        if "story_text" in story and story["story_text"]:
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
            formatted = {
                "author": comment.get("author"),
                "text": comment.get("text", ""),
                "created_at": comment.get("created_at"),
            }
            
            if depth > 1 and comment.get("children"):
                formatted["replies"] = self._format_comments(
                    comment["children"],
                    depth=depth - 1,
                    max_per_level=max_per_level,
                )
            
            result.append(formatted)
        
        return result


# Singleton client instance for resource use
_global_client: HNClient | None = None


async def get_client() -> HNClient:
    """Get or create the global HN client."""
    global _global_client
    if _global_client is None:
        _global_client = HNClient()
        await _global_client.__aenter__()
    return _global_client
