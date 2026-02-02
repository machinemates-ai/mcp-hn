"""
Article Content Extraction.

Fetches and converts article HTML to Markdown.
Inspired by GeorgeNance/hackernews-mcp's turndown-based approach.
"""

from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify as md

from hn_mcp.cache import cached

# Blocked private IP ranges for security
BLOCKED_HOSTS = frozenset([
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "10.",
    "172.16.", "172.17.", "172.18.", "172.19.",
    "172.20.", "172.21.", "172.22.", "172.23.",
    "172.24.", "172.25.", "172.26.", "172.27.",
    "172.28.", "172.29.", "172.30.", "172.31.",
    "192.168.",
])

# Content type whitelist
ALLOWED_CONTENT_TYPES = frozenset([
    "text/html",
    "text/plain",
    "application/xhtml+xml",
])

# Max content size (5MB)
MAX_CONTENT_SIZE = 5 * 1024 * 1024


class ContentExtractionError(Exception):
    """Raised when content extraction fails."""

    pass


def _is_blocked_host(url: str) -> bool:
    """Check if the URL host is a blocked private IP."""
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""

        # Check exact matches
        if host in BLOCKED_HOSTS:
            return True

        # Check prefix matches (for IP ranges)
        for prefix in BLOCKED_HOSTS:
            if prefix.endswith(".") and host.startswith(prefix):
                return True

        return False
    except Exception:
        return True  # Block on parse error


def _extract_article_content(html: str) -> str:
    """
    Extract main article content from HTML and convert to Markdown.

    Uses heuristics to find the main content area.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove script, style, nav, header, footer elements
    for element in soup.find_all([
        "script", "style", "nav", "header", "footer", "aside", "iframe"
    ]):
        element.decompose()

    # Try to find main content
    content = None

    # 1. Look for <article> tag
    article = soup.find("article")
    if article:
        content = article

    # 2. Look for common content containers
    if not content:
        selectors = [
            "main",
            ".content",
            ".post-content",
            ".article-content",
            ".entry-content",
            "#content",
        ]
        for selector in selectors:
            if selector.startswith((".", "#")):
                found = soup.select_one(selector)
            else:
                found = soup.find(selector)
            if found:
                content = found
                break

    # 3. Fall back to body
    if not content:
        content = soup.body or soup

    # Convert to markdown
    try:
        markdown_content = md(
            str(content),
            heading_style="ATX",
            strip=["img", "script", "style"],
        )
    except Exception:
        # Fallback to plain text
        markdown_content = content.get_text(separator="\n", strip=True)

    # Clean up excessive whitespace
    lines = [line.strip() for line in markdown_content.split("\n")]
    cleaned = "\n".join(line for line in lines if line)

    # Limit length
    max_chars = 50000
    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars] + "\n\n[Content truncated...]"

    return cleaned


@cached("article_content")
async def fetch_article_content(url: str) -> dict[str, str]:
    """
    Fetch and extract article content as Markdown.

    Args:
        url: The article URL

    Returns:
        Dictionary with 'url', 'title', 'content' (markdown)

    Raises:
        ContentExtractionError: If fetching or extraction fails
    """
    if not url or not url.startswith(("http://", "https://")):
        raise ContentExtractionError(f"Invalid URL: {url}")

    if _is_blocked_host(url):
        raise ContentExtractionError(f"Blocked host: {url}")

    try:
        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; mcp-hn/1.0; "
                    "+https://github.com/machinemates-ai/mcp-hn)"
                ),
                "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            },
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

            # Check content type
            content_type = response.headers.get("content-type", "")
            content_type = content_type.split(";")[0].strip()
            if content_type and content_type not in ALLOWED_CONTENT_TYPES:
                raise ContentExtractionError(
                    f"Unsupported content type: {content_type}"
                )

            # Check content size
            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > MAX_CONTENT_SIZE:
                raise ContentExtractionError(
                    f"Content too large: {content_length} bytes"
                )

            html = response.text

            # Extract title
            soup = BeautifulSoup(html, "html.parser")
            title_tag = soup.find("title")
            title = title_tag.get_text(strip=True) if title_tag else ""

            # Extract content as markdown
            content = _extract_article_content(html)

            return {
                "url": str(response.url),  # Final URL after redirects
                "title": title,
                "content": content,
            }

    except httpx.HTTPStatusError as e:
        raise ContentExtractionError(
            f"HTTP {e.response.status_code}: {url}"
        ) from e
    except httpx.TimeoutException as e:
        raise ContentExtractionError(f"Timeout fetching: {url}") from e
    except httpx.RequestError as e:
        raise ContentExtractionError(f"Request error: {e}") from e
