"""
MCP-HN: Hacker News MCP Server

A FastMCP 3.0 server providing Tools, Resources, and Prompts for Hacker News.

Features:
- Async httpx for non-blocking HTTP requests
- LRU caching with adaptive TTLs
- MCP Resources (hackernews:// URIs)
- Both Algolia and Firebase HN APIs
- Article content extraction to Markdown

Backward compatible with erithwik/mcp-hn tool names.
"""

from mcp_hn.server import main

__all__ = ["main"]
