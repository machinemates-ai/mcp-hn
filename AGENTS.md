# HN-MCP Agent Instructions

## Project Overview
This is an MCP (Model Context Protocol) server for Hacker News, built with FastMCP 3.0.

## Architecture

```
src/hn_mcp/
├── __init__.py     # Package exports
├── server.py       # FastMCP server - tools, resources, prompts
├── client.py       # Async HN API client (Algolia + Firebase)
├── cache.py        # LRU cache with adaptive TTLs
└── content.py      # Article content extraction to Markdown
```

## Key Design Decisions

1. **FastMCP 3.0** - Uses decorator-based patterns for tools, resources, prompts
2. **Async httpx** - Non-blocking HTTP for all API calls
3. **Dual API** - Algolia for search speed, Firebase for official data
4. **Adaptive caching** - Different TTLs per content type
5. **MCP Resources** - `hackernews://` URI scheme for story feeds

## MCP Capabilities

### Tools (Interactive)
- `get_stories` - Fetch by type (top/new/best/ask/show/job)
- `search_stories` - Search with relevance or date sorting
- `get_story` - Full story with nested comments
- `get_user` - User profile with submissions
- `fetch_article_content` - HTML to Markdown extraction
- `cache_stats` - Monitoring

### Resources (Read-only URIs)
- `hackernews://top|new|best|ask|show|jobs` - Story feeds
- `hackernews://story/{id}` - Story template
- `hackernews://user/{username}` - User template

### Prompts (Templates)
- `summarize_hn` - Top stories summary
- `analyze_discussion` - Comment analysis
- `compare_coverage` - Topic comparison

## Development

```bash
# Install dependencies
uv pip install -e ".[dev]"

# Run server
hn-mcp

# Run tests
pytest
```

## Extending

Add new tools with:
```python
@mcp.tool(name="my_tool", description="...")
async def my_tool(...) -> str:
    ...
```

Add new resources with:
```python
@mcp.resource(uri="hackernews://new-feed", ...)
async def my_resource() -> str:
    ...
```
