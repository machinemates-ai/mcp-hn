"""
Article Content Extraction.

Fetches and extracts article content as Markdown using trafilatura.
Trafilatura is the gold standard for web article extraction (F1: 0.937).

Security: Includes SSRF protection by blocking private IPs and cloud metadata endpoints.
"""

from ipaddress import IPv4Address, IPv6Address, ip_address
from urllib.parse import urlparse

import httpx
import trafilatura

from hn_mcp.cache import cached

# Blocked private IP ranges for SSRF protection
# Includes: localhost, private ranges (RFC 1918), cloud metadata endpoints
BLOCKED_HOSTS = frozenset([
    # Localhost
    "localhost",
    # Cloud metadata endpoints (CRITICAL for SSRF protection)
    "metadata.google.internal",  # GCP alternative
    "metadata",  # Kubernetes
])

# Private IP range prefixes (RFC 1918 + link-local) - for fallback string matching
BLOCKED_PREFIXES = frozenset([
    "10.",           # 10.0.0.0/8
    "172.16.", "172.17.", "172.18.", "172.19.",  # 172.16.0.0/12
    "172.20.", "172.21.", "172.22.", "172.23.",
    "172.24.", "172.25.", "172.26.", "172.27.",
    "172.28.", "172.29.", "172.30.", "172.31.",
    "192.168.",      # 192.168.0.0/16
    "169.254.",      # Link-local (AWS metadata range)
    "100.64.",       # Carrier-grade NAT (RFC 6598)
    "100.65.", "100.66.", "100.67.", "100.68.", "100.69.",
    "100.70.", "100.71.", "100.72.", "100.73.", "100.74.",
    "100.75.", "100.76.", "100.77.", "100.78.", "100.79.",
    "100.80.", "100.81.", "100.82.", "100.83.", "100.84.",
    "100.85.", "100.86.", "100.87.", "100.88.", "100.89.",
    "100.90.", "100.91.", "100.92.", "100.93.", "100.94.",
    "100.95.", "100.96.", "100.97.", "100.98.", "100.99.",
    "100.100.", "100.101.", "100.102.", "100.103.", "100.104.",
    "100.105.", "100.106.", "100.107.", "100.108.", "100.109.",
    "100.110.", "100.111.", "100.112.", "100.113.", "100.114.",
    "100.115.", "100.116.", "100.117.", "100.118.", "100.119.",
    "100.120.", "100.121.", "100.122.", "100.123.", "100.124.",
    "100.125.", "100.126.", "100.127.",
    "fd",            # IPv6 private (fd00::/8)
    "fe80:",         # IPv6 link-local
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
    """Check if the URL host is a blocked private IP or cloud metadata endpoint.
    
    Uses Python's ipaddress module for robust IP validation including:
    - IPv4 private ranges (10.x, 172.16-31.x, 192.168.x)
    - IPv6 private ranges  
    - IPv4-mapped IPv6 addresses (::ffff:127.0.0.1)
    - Loopback addresses
    - Link-local addresses
    - Cloud metadata endpoints
    """
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        
        # Strip brackets from IPv6 addresses
        if host.startswith('[') and host.endswith(']'):
            host = host[1:-1]

        # Check exact matches (localhost, metadata endpoints)
        if host in BLOCKED_HOSTS:
            return True

        # Try to parse as IP address for robust checking
        try:
            addr = ip_address(host)
            
            # Check for IPv4-mapped IPv6 (::ffff:x.x.x.x)
            if isinstance(addr, IPv6Address) and addr.ipv4_mapped:
                # Check the underlying IPv4 address
                ipv4 = addr.ipv4_mapped
                if ipv4.is_private or ipv4.is_loopback or ipv4.is_link_local:
                    return True
                # Also check for cloud metadata IP
                if str(ipv4) == "169.254.169.254":
                    return True
            
            # Standard checks via ipaddress module
            if addr.is_private:
                return True
            if addr.is_loopback:
                return True
            if addr.is_link_local:
                return True
            if addr.is_reserved:
                return True
            if addr.is_multicast:
                return True
            
            # Additional check: cloud metadata endpoint
            if isinstance(addr, IPv4Address) and str(addr) == "169.254.169.254":
                return True
                
            return False
            
        except ValueError:
            # Not a valid IP address, check as hostname
            pass

        # Check prefix matches (for hostnames/edge cases)
        for prefix in BLOCKED_PREFIXES:
            if host.startswith(prefix):
                return True

        return False
    except Exception:
        return True  # Block on parse error


def _extract_article_content(html: str) -> str:
    """
    Extract main article content from HTML and convert to Markdown.

    Uses trafilatura for superior article extraction accuracy (F1: 0.937).
    Automatically removes navigation, ads, footers, and other boilerplate.
    """
    # Trafilatura with markdown output - gold standard for article extraction
    markdown_content = trafilatura.extract(
        html,
        output_format="markdown",
        include_comments=False,
        include_tables=True,
        include_links=True,
        include_images=False,  # Skip images for cleaner text
        include_formatting=True,
        no_fallback=False,  # Use fallback extraction if main extraction fails
    )

    if not markdown_content:
        # Fallback: Try plain text extraction
        text_content = trafilatura.extract(
            html,
            output_format="txt",
            include_comments=False,
            no_fallback=False,
        )
        markdown_content = text_content or ""

    if not markdown_content:
        raise ContentExtractionError("Could not extract content from HTML")

    # Clean up and limit length
    cleaned = markdown_content.strip()

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

            # Extract title using trafilatura's metadata extraction
            metadata = trafilatura.extract_metadata(html)
            title = metadata.title if metadata and metadata.title else ""

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
