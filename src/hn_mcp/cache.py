"""
LRU Cache with TTL support for MCP-HN.

Inspired by karanb192/hn-mcp's caching strategy with adaptive TTLs.
"""

import asyncio
import hashlib
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar

from cachetools import TTLCache

# Type variables for generic typing
P = ParamSpec("P")
R = TypeVar("R")

# Cache configuration (inspired by karanb192/hn-mcp)
MAX_CACHE_ITEMS = 1000  # Max number of items

# Adaptive TTLs based on content type
TTL_CONFIGS: dict[str, int] = {
    "stories_list": 300,      # 5 min - story lists change frequently
    "story_detail": 600,      # 10 min - individual story details
    "user_info": 1800,        # 30 min - user info changes less often
    "search_results": 180,    # 3 min - search results can vary
    "article_content": 3600,  # 1 hour - article content rarely changes
    "default": 300,           # 5 min default
}


def _get_cache_key(func_name: str, *args: Any, **kwargs: Any) -> str:
    """Generate a cache key from function name and arguments."""
    key_parts = [func_name]
    key_parts.extend(str(arg) for arg in args)
    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    key_string = ":".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()


class HNCache:
    """
    Thread-safe LRU cache with TTL support for HN API responses.

    Features:
    - Separate caches per content type with different TTLs
    - Memory-aware size limits
    - Cache statistics for monitoring
    """

    def __init__(self) -> None:
        self._caches: dict[str, TTLCache[str, Any]] = {}
        self._hits = 0
        self._misses = 0
        self._lock = asyncio.Lock()

        # Initialize caches for each content type
        for cache_type, ttl in TTL_CONFIGS.items():
            max_items = MAX_CACHE_ITEMS // len(TTL_CONFIGS)
            self._caches[cache_type] = TTLCache(maxsize=max_items, ttl=ttl)

    async def get(self, cache_type: str, key: str) -> Any | None:
        """Get item from cache if not expired."""
        async with self._lock:
            cache = self._caches.get(cache_type, self._caches["default"])
            try:
                value = cache[key]
                self._hits += 1
                return value
            except KeyError:
                self._misses += 1
                return None

    async def set(self, cache_type: str, key: str, value: Any) -> None:
        """Store item in cache."""
        async with self._lock:
            cache = self._caches.get(cache_type, self._caches["default"])
            cache[key] = value

    async def clear(self, cache_type: str | None = None) -> None:
        """Clear cache(s)."""
        async with self._lock:
            if cache_type:
                if cache_type in self._caches:
                    self._caches[cache_type].clear()
            else:
                for cache in self._caches.values():
                    cache.clear()

    def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total_items = sum(len(cache) for cache in self._caches.values())
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0
        return {
            "total_items": total_items,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.1%}",
            "caches": {name: len(cache) for name, cache in self._caches.items()},
        }


# Global cache instance
_cache = HNCache()


def cached(
    cache_type: str = "default",
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """
    Decorator for caching async function results.

    Usage:
        @cached("stories_list")
        async def get_stories(...):
            ...
    """

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            key = _get_cache_key(func.__name__, *args, **kwargs)

            # Try cache first
            cached_value = await _cache.get(cache_type, key)
            if cached_value is not None:
                return cached_value

            # Call function and cache result
            result = await func(*args, **kwargs)
            await _cache.set(cache_type, key, result)
            return result

        return wrapper

    return decorator


def get_cache() -> HNCache:
    """Get the global cache instance."""
    return _cache
