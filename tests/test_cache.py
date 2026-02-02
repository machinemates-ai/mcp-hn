"""Tests for the cache module."""

import pytest

from mcp_hn.cache import HNCache, cached


class TestHNCache:
    """Test cases for HNCache."""

    @pytest.mark.asyncio
    async def test_cache_set_get(self):
        """Test basic cache set and get."""
        cache = HNCache()
        await cache.set("default", "test_key", {"data": "value"})
        result = await cache.get("default", "test_key")
        assert result == {"data": "value"}

    @pytest.mark.asyncio
    async def test_cache_miss(self):
        """Test cache miss returns None."""
        cache = HNCache()
        result = await cache.get("default", "nonexistent_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_stats(self):
        """Test cache statistics."""
        cache = HNCache()
        
        # Generate some hits and misses
        await cache.get("default", "miss1")  # miss
        await cache.set("default", "key1", "value1")
        await cache.get("default", "key1")  # hit
        
        stats = cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1

    @pytest.mark.asyncio
    async def test_cached_decorator(self):
        """Test the cached decorator."""
        call_count = 0
        
        @cached("default")
        async def expensive_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2
        
        # First call - should execute function
        result1 = await expensive_function(5)
        assert result1 == 10
        assert call_count == 1
        
        # Second call with same args - should return cached
        result2 = await expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # Not incremented
        
        # Call with different args - should execute function
        result3 = await expensive_function(10)
        assert result3 == 20
        assert call_count == 2
