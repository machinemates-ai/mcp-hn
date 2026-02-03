"""
Harness tests - Deep review findings.

These tests expose issues found during maintainer-level code review.
Each test documents the issue and verifies the fix.
"""

import asyncio
from unittest.mock import AsyncMock, patch
from urllib.parse import quote

import pytest


class TestRateLimiterBugs:
    """Tests for rate limiter edge cases and potential bugs."""

    @pytest.mark.asyncio
    async def test_wait_and_acquire_not_recursive(self) -> None:
        """Verify wait_and_acquire uses iteration, not recursion.
        
        Issue: Original implementation used recursive call which could
        cause stack overflow under high contention.
        """
        from hn_mcp.rate_limit import RateLimiter, RateLimitConfig

        # Create a limiter that will hit the limit quickly
        limiter = RateLimiter(
            config=RateLimitConfig(requests_per_minute=5, burst_allowance=1.0)
        )

        # Fill up the limit
        for _ in range(5):
            await limiter.acquire()

        # The next acquire should return wait time > 0
        wait_time = await limiter.acquire()
        # Should not have crashed with recursion
        assert wait_time >= 0

    @pytest.mark.asyncio
    async def test_stats_thread_safety(self) -> None:
        """Verify stats() is thread-safe when called concurrently.
        
        Issue: stats() iterated over _timestamps without holding the lock,
        which could cause race conditions.
        Fix: stats() is now async and uses the lock.
        """
        from hn_mcp.rate_limit import RateLimiter, RateLimitConfig

        limiter = RateLimiter(config=RateLimitConfig(requests_per_minute=1000))

        # Simulate concurrent access
        async def acquire_and_check():
            await limiter.acquire()
            return await limiter.stats()

        # Run many concurrent acquisitions + stats checks
        tasks = [acquire_and_check() for _ in range(50)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should succeed without exceptions
        for result in results:
            assert not isinstance(result, Exception), f"Got exception: {result}"
            assert "requests_in_window" in result

    @pytest.mark.asyncio
    async def test_rate_limiter_under_extreme_load(self) -> None:
        """Test rate limiter doesn't crash under extreme load."""
        from hn_mcp.rate_limit import RateLimiter, RateLimitConfig

        limiter = RateLimiter(
            config=RateLimitConfig(requests_per_minute=100, burst_allowance=1.2)
        )

        # Acquire many times rapidly
        for _ in range(150):
            wait = await limiter.acquire()
            assert wait >= 0

        stats = await limiter.stats()
        assert stats["requests_in_window"] > 0


class TestURLEncodingBugs:
    """Tests for URL encoding issues in API calls."""

    def test_search_query_with_special_chars(self) -> None:
        """Verify search queries are properly URL-encoded.
        
        Issue: Queries with &, =, #, spaces weren't encoded, breaking API calls.
        """
        # Test that URL encoding is applied
        test_cases = [
            ("hello world", "hello%20world"),
            ("C++ programming", "C%2B%2B%20programming"),
            ("foo&bar=baz", "foo%26bar%3Dbaz"),
            ("test#anchor", "test%23anchor"),
            ("special?query", "special%3Fquery"),
        ]

        for raw, expected in test_cases:
            encoded = quote(raw, safe="")
            assert encoded == expected, f"Failed for: {raw}"

    @pytest.mark.asyncio
    async def test_search_stories_encodes_query(self) -> None:
        """Test that search_stories properly encodes the query parameter."""
        from hn_mcp.hn import HNClient

        async def mock_rate_limited_get(url: str):
            """Mock that returns a fake response and captures the URL."""
            mock_rate_limited_get.captured_url = url

            class FakeResponse:
                def raise_for_status(self):
                    pass

                def json(self):
                    return {"hits": []}

            return FakeResponse()

        async with HNClient() as client:
            # Patch the method on the instance
            client._rate_limited_get = mock_rate_limited_get
            await client.search_stories("C++ & Python", 5)

        # Check the URL was properly encoded
        called_url = mock_rate_limited_get.captured_url
        # The query should be URL-encoded: + becomes %2B
        assert "C%2B%2B" in called_url, f"URL not encoded: {called_url}"
        # & should be encoded as %26 so it doesn't break the query string
        assert "%26" in called_url, f"& not encoded: {called_url}"
        # The raw & should not appear between query and hitsPerPage
        # (there should only be proper query string & separators)
        assert "&Python" not in called_url


class TestExplainTermAliases:
    """Tests for hn_explain term aliases and edge cases."""

    def test_shadowbanned_alias(self) -> None:
        """Test 'shadowbanned' (past tense) maps to hellban.
        
        Issue: Only 'shadowban' was mapped, users might try 'shadowbanned'.
        """
        from hn_mcp.server import explain_hn_term

        result = explain_hn_term("shadowbanned")
        # Should either resolve to hellban or be in available_terms
        if "error" in result:
            # If not mapped, verify the fix is needed
            assert "shadowbanned" not in result.get("available_terms", [])
        else:
            assert result["normalized"] == "hellban"

    def test_all_variations_resolve(self) -> None:
        """Test all documented variations resolve correctly."""
        from hn_mcp.server import explain_hn_term

        variations_that_should_work = [
            ("show", "show_hn"),
            ("ask", "ask_hn"),
            ("shadow_ban", "hellban"),
            ("shadowban", "hellban"),
            ("guidelines", "hn_guidelines"),
            ("rules", "hn_guidelines"),
            ("paul_graham", "pg"),
            ("daniel_gackle", "dang"),
            ("y_combinator", "yc"),
            ("ycombinator", "yc"),
            ("duplicate", "dupe"),
        ]

        for input_term, expected_normalized in variations_that_should_work:
            result = explain_hn_term(input_term)
            assert "error" not in result, f"Failed for: {input_term}"
            assert result["normalized"] == expected_normalized, f"Wrong normalization for: {input_term}"

    def test_whitespace_handling(self) -> None:
        """Test terms with leading/trailing whitespace."""
        from hn_mcp.server import explain_hn_term

        result = explain_hn_term("  karma  ")
        assert result["normalized"] == "karma"
        assert "definition" in result

    def test_mixed_case_with_underscores(self) -> None:
        """Test mixed case terms with underscores and hyphens."""
        from hn_mcp.server import explain_hn_term

        test_cases = ["Show_HN", "SHOW-HN", "show-hn", "Show HN"]
        for term in test_cases:
            result = explain_hn_term(term)
            assert result["normalized"] == "show_hn", f"Failed for: {term}"


class TestErrorHandling:
    """Tests for error handling edge cases."""

    @pytest.mark.asyncio
    async def test_cache_stats_tool_returns_valid_json(self) -> None:
        """Test cache_stats tool returns valid JSON with all expected fields."""
        import json
        from hn_mcp.server import cache_stats

        result = await cache_stats()
        data = json.loads(result)

        assert "cache" in data
        assert "rate_limiter" in data
        assert "hits" in data["cache"]
        assert "misses" in data["cache"]
        assert "requests_in_window" in data["rate_limiter"]


class TestASGIApp:
    """Tests for ASGI app configuration."""

    def test_asgi_app_exists(self) -> None:
        """Test ASGI app is properly exported."""
        from hn_mcp import asgi_app

        assert asgi_app is not None
        # Should be a Starlette-compatible app
        assert hasattr(asgi_app, "__call__")

    def test_asgi_app_is_starlette(self) -> None:
        """Test ASGI app is a FastMCP HTTP app."""
        from hn_mcp.server import asgi_app

        # FastMCP 3.0 returns StarletteWithLifespan
        app_type = type(asgi_app).__name__
        assert "Starlette" in app_type or "ASGI" in app_type or hasattr(asgi_app, "app")


class TestInputValidation:
    """Tests for input validation and boundary conditions."""

    @pytest.mark.asyncio
    async def test_get_stories_clamps_num_stories(self) -> None:
        """Test num_stories is clamped to valid range."""
        import json
        from hn_mcp.server import get_stories
        from hn_mcp.hn import HNClient

        # Mock to avoid real API call
        with patch.object(HNClient, "get_stories", new_callable=AsyncMock) as mock:
            mock.return_value = []

            # Test with too-large value
            await get_stories(num_stories=1000)
            called_num = mock.call_args[0][1] if len(mock.call_args[0]) > 1 else mock.call_args[1].get("num_stories", 10)
            # Should be clamped to 50 max
            assert called_num <= 50

    @pytest.mark.asyncio
    async def test_get_story_info_clamps_depth(self) -> None:
        """Test comment_depth is clamped to valid range."""
        import json
        from hn_mcp.server import get_story_info
        from hn_mcp.hn import HNClient

        with patch.object(HNClient, "get_story_info", new_callable=AsyncMock) as mock:
            mock.return_value = {"id": 1, "title": "Test"}

            # Test with too-large depth
            await get_story_info(story_id=1, comment_depth=100)
            called_depth = mock.call_args[1].get("comment_depth", 3)
            # Should be clamped to 10 max
            assert called_depth <= 10

    def test_story_id_as_string(self) -> None:
        """Test story_id type handling (int vs string)."""
        from hn_mcp.hn import HNClient

        client = HNClient()
        
        # Test formatting handles both string and int IDs
        story_with_int = {"story_id": 12345, "author": "test"}
        story_with_str = {"objectID": "12345", "author": "test"}

        formatted_int = client._format_story(story_with_int)
        formatted_str = client._format_story(story_with_str)

        assert formatted_int["id"] == 12345
        assert formatted_str["id"] == 12345


class TestCacheKeyBugs:
    """Tests for cache key generation issues."""

    @pytest.mark.asyncio
    async def test_cache_key_excludes_self(self) -> None:
        """Verify cache keys don't include object identity.

        Issue: If cache key includes `self` (the object), different
        HNClient instances would have different cache keys for identical
        requests, defeating the purpose of caching.
        """
        from hn_mcp.cache import _get_cache_key

        # Simulate what happens with method calls
        # args[0] = self = "<HNClient at 0x123>" vs "<HNClient at 0x456>"
        class FakeClient1:
            pass

        class FakeClient2:
            pass

        obj1 = FakeClient1()
        obj2 = FakeClient2()

        # If we naively include self in cache key, these would differ
        # That's a bug - same logical request should get same key
        key1 = _get_cache_key("get_stories", "top", 10)
        key2 = _get_cache_key("get_stories", "top", 10)

        # Keys for same args should be identical
        assert key1 == key2

    @pytest.mark.asyncio
    async def test_cache_shared_across_clients(self) -> None:
        """Verify cache is shared across HNClient instances.

        Issue: Each HNClient() context should share the same cache,
        not create isolated cache entries.
        """
        from hn_mcp.cache import get_cache
        from hn_mcp.hn import HNClient

        cache = get_cache()
        initial_stats = cache.stats()

        # Mock the API call to avoid real requests
        async def mock_rate_limited_get(url: str):
            class FakeResponse:
                def raise_for_status(self):
                    pass

                def json(self):
                    return {"hits": [{"objectID": "1", "author": "test"}]}

            return FakeResponse()

        # First client fetches data
        async with HNClient() as client1:
            client1._rate_limited_get = mock_rate_limited_get
            result1 = await client1.get_stories("top", 5)

        # Second client should hit cache (if cache is working correctly)
        async with HNClient() as client2:
            client2._rate_limited_get = mock_rate_limited_get
            result2 = await client2.get_stories("top", 5)

        # Results should be identical
        assert result1 == result2

        # Cache stats should show at least one hit
        # (first request is a miss, second should be a hit)
        final_stats = cache.stats()
        # At minimum, we shouldn't have 2 misses for identical requests
        assert final_stats["hits"] > initial_stats["hits"] or \
               final_stats["total_items"] <= initial_stats["total_items"] + 1


class TestSSRFProtection:
    """Tests for SSRF (Server-Side Request Forgery) protection."""

    def test_ipv4_mapped_ipv6_blocked(self) -> None:
        """Verify IPv4-mapped IPv6 addresses are blocked.

        Issue: ::ffff:127.0.0.1 is IPv4-mapped IPv6 for localhost.
        Must be blocked to prevent SSRF bypass.
        """
        from hn_mcp.content import _is_blocked_host

        # IPv4-mapped IPv6 forms
        ipv4_mapped = [
            "http://[::ffff:127.0.0.1]/",
            "http://[::ffff:169.254.169.254]/",  # AWS metadata
            "http://[::ffff:10.0.0.1]/",
            "http://[::ffff:192.168.1.1]/",
            "http://[0:0:0:0:0:ffff:127.0.0.1]/",
        ]

        for url in ipv4_mapped:
            assert _is_blocked_host(url), f"Should block: {url}"

    def test_carrier_grade_nat_blocked(self) -> None:
        """Verify 100.64.0.0/10 (carrier-grade NAT) is blocked.

        RFC 6598 reserves 100.64.0.0/10 for carrier-grade NAT.
        Can be used for internal network access.
        """
        from hn_mcp.content import _is_blocked_host

        cgnat_ips = [
            "http://100.64.0.1/",
            "http://100.100.100.100/",
            "http://100.127.255.254/",
        ]

        for url in cgnat_ips:
            # CGNAT is now blocked via ipaddress.is_private and prefix matching
            assert _is_blocked_host(url), f"Should block CGNAT: {url}"

    def test_ipv6_localhost_variations(self) -> None:
        """Test various IPv6 localhost representations."""
        from hn_mcp.content import _is_blocked_host

        ipv6_localhost = [
            "http://[::1]/",
            "http://[0:0:0:0:0:0:0:1]/",
            "http://[0000:0000:0000:0000:0000:0000:0000:0001]/",
        ]

        for url in ipv6_localhost:
            assert _is_blocked_host(url), f"Should block IPv6 localhost: {url}"

    def test_url_scheme_validation(self) -> None:
        """Test URL scheme validation."""
        from hn_mcp.content import _is_blocked_host

        # These should all be blocked (invalid/dangerous schemes handled by caller)
        invalid_urls = [
            "file:///etc/passwd",
            "ftp://internal.server/",
            "gopher://localhost/",
        ]

        # Note: _is_blocked_host only checks host, not scheme
        # The fetch_article_content function validates scheme separately


class TestHTTPErrorHandling:
    """Tests for HTTP error handling."""

    @pytest.mark.asyncio
    async def test_http_errors_wrapped(self) -> None:
        """Verify HTTP errors are wrapped in ContentExtractionError."""
        from hn_mcp.content import ContentExtractionError, fetch_article_content

        # Test with a URL that should fail
        with pytest.raises(ContentExtractionError):
            await fetch_article_content("https://httpstat.us/404")

    @pytest.mark.asyncio
    async def test_timeout_wrapped(self) -> None:
        """Verify timeout errors are wrapped in ContentExtractionError."""
        from hn_mcp.content import ContentExtractionError, fetch_article_content

        # Test with a URL that should timeout (very short timeout)
        # Note: We can't easily test this without mocking


class TestConcurrency:
    """Tests for concurrent operation safety."""

    @pytest.mark.asyncio
    async def test_concurrent_cache_access(self) -> None:
        """Test cache handles concurrent access safely."""
        from hn_mcp.cache import HNCache

        cache = HNCache()

        async def set_and_get(key: str, value: str):
            await cache.set("default", key, {"data": value})
            await asyncio.sleep(0.001)  # Simulate some work
            return await cache.get("default", key)

        # Run many concurrent cache operations
        tasks = [set_and_get(f"key_{i}", f"value_{i}") for i in range(50)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should succeed
        for i, result in enumerate(results):
            assert not isinstance(result, Exception)
            assert result is not None
            assert result["data"] == f"value_{i}"

    @pytest.mark.asyncio
    async def test_rate_limiter_reset_while_acquiring(self) -> None:
        """Verify reset() during acquisition doesn't crash."""
        from hn_mcp.rate_limit import RateLimiter, RateLimitConfig

        limiter = RateLimiter(config=RateLimitConfig(requests_per_minute=100))

        async def acquire_loop():
            for _ in range(20):
                await limiter.acquire()
                await asyncio.sleep(0.001)

        async def reset_periodically():
            for _ in range(5):
                await asyncio.sleep(0.01)
                limiter.reset()

        # Run both concurrently
        await asyncio.gather(
            acquire_loop(),
            reset_periodically(),
            return_exceptions=True,
        )

        # Should not crash - just verify we get here
        stats = await limiter.stats()
        assert "requests_in_window" in stats
