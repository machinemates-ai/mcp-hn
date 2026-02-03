"""
HN-MCP: Hacker News MCP Server

A FastMCP server providing Tools, Resources, and Prompts for Hacker News.

Features:
- Async httpx for non-blocking HTTP requests
- LRU caching with adaptive TTLs
- MCP Resources (hackernews:// URIs)
- Both Algolia and Firebase HN APIs
- Article content extraction to Markdown
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("hn-mcp")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"

from hn_mcp.server import asgi_app, main, mcp

__all__ = ["__version__", "asgi_app", "main", "mcp"]
