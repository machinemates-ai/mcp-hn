"""
Unit tests for mcp_hn.content module (article extraction).
"""

import pytest

from hn_mcp.content import (
    ContentExtractionError,
    _extract_article_content,
    _is_blocked_host,
)


class TestBlockedHosts:
    """Tests for private IP blocking."""

    def test_localhost_blocked(self) -> None:
        """Test localhost is blocked."""
        assert _is_blocked_host("http://localhost/page") is True
        assert _is_blocked_host("http://127.0.0.1/page") is True

    def test_private_ips_blocked(self) -> None:
        """Test private IP ranges are blocked."""
        assert _is_blocked_host("http://10.0.0.1/page") is True
        assert _is_blocked_host("http://172.16.0.1/page") is True
        assert _is_blocked_host("http://192.168.1.1/page") is True

    def test_public_urls_allowed(self) -> None:
        """Test public URLs are allowed."""
        assert _is_blocked_host("https://example.com/page") is False
        assert _is_blocked_host("https://news.ycombinator.com") is False

    def test_invalid_url_blocked(self) -> None:
        """Test invalid URLs without scheme are handled."""
        # URLs without scheme are not blocked - they fail later during fetch
        assert _is_blocked_host("not-a-url") is False


class TestContentExtraction:
    """Tests for HTML to Markdown extraction."""

    def test_extract_article_tag(self) -> None:
        """Test extraction from <article> tag."""
        html = """
        <html>
            <body>
                <nav>Navigation</nav>
                <article>
                    <h1>Title</h1>
                    <p>Content paragraph.</p>
                </article>
                <footer>Footer</footer>
            </body>
        </html>
        """
        result = _extract_article_content(html)
        assert "Title" in result
        assert "Content paragraph" in result
        assert "Navigation" not in result
        assert "Footer" not in result

    def test_extract_main_tag(self) -> None:
        """Test extraction from <main> tag."""
        html = """
        <html>
            <body>
                <header>Header</header>
                <main>
                    <p>Main content here.</p>
                </main>
            </body>
        </html>
        """
        result = _extract_article_content(html)
        assert "Main content" in result
        assert "Header" not in result

    def test_extract_removes_scripts(self) -> None:
        """Test that script tags are removed."""
        html = """
        <html>
            <body>
                <script>alert('evil')</script>
                <p>Safe content</p>
            </body>
        </html>
        """
        result = _extract_article_content(html)
        assert "Safe content" in result
        assert "alert" not in result
        assert "evil" not in result

    def test_extract_fallback_to_body(self) -> None:
        """Test fallback to body when no article/main found."""
        html = """
        <html>
            <body>
                <div>Just a div</div>
                <p>Paragraph content</p>
            </body>
        </html>
        """
        result = _extract_article_content(html)
        assert "Paragraph content" in result


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
