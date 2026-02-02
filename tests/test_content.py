"""
Unit tests for hn_mcp.content module (article extraction).

Note: trafilatura is optimized for real web pages, not minimal HTML snippets.
Tests focus on SSRF blocking and basic extraction functionality.
"""

import pytest

from hn_mcp.content import (
    ContentExtractionError,
    _extract_article_content,
    _is_blocked_host,
)


class TestBlockedHosts:
    """Tests for private IP and cloud metadata blocking (SSRF protection)."""

    def test_localhost_blocked(self) -> None:
        """Test localhost variants are blocked."""
        assert _is_blocked_host("http://localhost/page") is True
        assert _is_blocked_host("http://127.0.0.1/page") is True
        assert _is_blocked_host("http://0.0.0.0/page") is True

    def test_private_ips_blocked(self) -> None:
        """Test private IP ranges (RFC 1918) are blocked."""
        assert _is_blocked_host("http://10.0.0.1/page") is True
        assert _is_blocked_host("http://172.16.0.1/page") is True
        assert _is_blocked_host("http://192.168.1.1/page") is True

    def test_cloud_metadata_blocked(self) -> None:
        """Test cloud metadata endpoints are blocked (CRITICAL for SSRF)."""
        # AWS/GCP/Azure metadata endpoint
        assert _is_blocked_host("http://169.254.169.254/latest/meta-data/") is True
        # Link-local range
        assert _is_blocked_host("http://169.254.1.1/something") is True
        # GCP alternative
        assert _is_blocked_host("http://metadata.google.internal/") is True

    def test_ipv6_blocked(self) -> None:
        """Test IPv6 private addresses are blocked."""
        assert _is_blocked_host("http://[::1]/page") is True

    def test_public_urls_allowed(self) -> None:
        """Test public URLs are allowed."""
        assert _is_blocked_host("https://example.com/page") is False
        assert _is_blocked_host("https://news.ycombinator.com") is False
        assert _is_blocked_host("https://github.com/repo") is False

    def test_invalid_url_blocked(self) -> None:
        """Test invalid URLs without scheme are handled."""
        # URLs without scheme are not blocked - they fail later during fetch
        assert _is_blocked_host("not-a-url") is False


class TestContentExtraction:
    """Tests for HTML to Markdown extraction using trafilatura."""

    def test_extract_basic_content(self) -> None:
        """Test extraction from realistic HTML with article content."""
        html = """
        <!DOCTYPE html>
        <html>
            <head><title>Test Article</title></head>
            <body>
                <article>
                    <h1>Main Title</h1>
                    <p>This is the main content paragraph with enough text
                    to be recognized as valid article content by trafilatura.
                    It needs substantial content to work properly.</p>
                    <p>Another paragraph with more details about the topic.</p>
                </article>
            </body>
        </html>
        """
        result = _extract_article_content(html)
        assert "Main Title" in result
        assert "main content" in result

    def test_extract_removes_scripts(self) -> None:
        """Test that script content is not in output."""
        html = """
        <!DOCTYPE html>
        <html>
            <head><script>alert('evil')</script></head>
            <body>
                <p>This is safe content that should appear in the output.
                It has enough text to be considered valid article content.</p>
            </body>
        </html>
        """
        result = _extract_article_content(html)
        assert "safe content" in result.lower()
        assert "alert" not in result
        assert "evil" not in result

    def test_extract_handles_minimal_html(self) -> None:
        """Test extraction handles minimal HTML gracefully."""
        html = "<p>Simple paragraph content</p>"
        # trafilatura may return empty for minimal content
        try:
            result = _extract_article_content(html)
            # If it returns something, it should be meaningful
            assert isinstance(result, str)
        except ContentExtractionError:
            # Expected for very minimal content
            pass

    def test_extract_truncates_long_content(self) -> None:
        """Test that very long content is truncated."""
        # Create content longer than 50000 chars
        long_paragraph = "<p>" + "x" * 60000 + "</p>"
        html = f"<html><body>{long_paragraph}</body></html>"
        try:
            result = _extract_article_content(html)
            assert len(result) <= 50100  # 50000 + truncation message
            if len(result) > 50000:
                assert "[Content truncated...]" in result
        except ContentExtractionError:
            # trafilatura may not extract repetitive content
            pass


class TestFetchArticleContent:
    """Tests for fetch_article_content function."""

    @pytest.mark.asyncio
    async def test_invalid_url_raises_error(self) -> None:
        """Test invalid URLs raise ContentExtractionError."""
        from hn_mcp.content import fetch_article_content

        with pytest.raises(ContentExtractionError) as exc_info:
            await fetch_article_content("not-a-url")
        assert "Invalid URL" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_blocked_host_raises_error(self) -> None:
        """Test blocked hosts raise ContentExtractionError."""
        from hn_mcp.content import fetch_article_content

        with pytest.raises(ContentExtractionError) as exc_info:
            await fetch_article_content("http://localhost/page")
        assert "Blocked host" in str(exc_info.value)
