# HN-MCP 🔥

[![PyPI](https://img.shields.io/pypi/v/hn-mcp)](https://pypi.org/project/hn-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/hn-mcp)](https://pypi.org/project/hn-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) server for [Hacker News](https://news.ycombinator.com/), built with [FastMCP 3.0](https://gofastmcp.com/).

> Forked from [erithwik/mcp-hn](https://github.com/erithwik/mcp-hn) and enhanced with FastMCP 3.0, async httpx, caching, MCP Resources, and article content extraction.

## ✨ Features

- **🛠️ Tools** - Search stories, get story details, fetch user info, extract article content
- **📁 Resources** - Access story feeds via `hackernews://` URIs (top, new, best, ask, show, jobs)
- **📝 Prompts** - Templates for HN analysis and summarization
- **⚡ Async** - Full async/await with httpx for non-blocking requests
- **🗂️ Caching** - LRU cache with adaptive TTLs (inspired by [karanb192/hn-mcp](https://github.com/karanb192/hn-mcp))
- **📰 Content Extraction** - Fetch and convert article HTML to Markdown
- **🔒 Security** - Private IP blocking for URL fetching

## 📦 Installation

```bash
# Using pip
pip install hn-mcp

# Using uv (recommended)
uv pip install hn-mcp
```

## 🚀 Quick Start

### CLI

```bash
# Run the server
hn-mcp
```

### Programmatic

```python
from hn_mcp import mcp

if __name__ == "__main__":
    mcp.run()
```

## ⚙️ MCP Client Configuration

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "hn-mcp": {
      "command": "uvx",
      "args": ["hn-mcp"]
    }
  }
}
```

### VS Code with Copilot

Add to `.vscode/settings.json` or user settings:

```json
{
  "mcp.servers": {
    "hn-mcp": {
      "command": "uvx",
      "args": ["hn-mcp"]
    }
  }
}
```

### Cursor

Add to the MCP configuration in Cursor settings:

```json
{
  "hn-mcp": {
    "command": "uvx", 
    "args": ["hn-mcp"]
  }
}
```

## 🛠️ Tools

| Tool | Description |
|------|-------------|
| `get_stories` | Get stories by type (top, new, best, ask, show, job) |
| `search_stories` | Search HN stories with optional date sorting |
| `get_story` | Get story details with comments |
| `get_user` | Get user profile and submissions |
| `fetch_article_content` | Extract article content as Markdown |
| `cache_stats` | View cache statistics |

### Examples

```
# Get top 10 stories
get_stories(story_type="top", num_stories=10)

# Search for AI stories
search_stories(query="AI", num_results=20, search_by_date=True)

# Get story with comments
get_story(story_id=12345678, include_comments=True, comment_depth=3)

# Fetch article content
fetch_article_content(url="https://example.com/article")
```

## 📁 Resources

Access story feeds directly via URI:

| URI | Description |
|-----|-------------|
| `hackernews://top` | Front page stories |
| `hackernews://new` | Newest stories |
| `hackernews://best` | Highest voted stories |
| `hackernews://ask` | Ask HN posts |
| `hackernews://show` | Show HN posts |
| `hackernews://jobs` | Job postings |
| `hackernews://story/{id}` | Story details with comments |
| `hackernews://user/{username}` | User profile |

## 📝 Prompts

| Prompt | Description |
|--------|-------------|
| `summarize_hn` | Summarize current top stories |
| `analyze_discussion` | Analyze comments on a story |
| `compare_coverage` | Compare HN coverage of a topic |

## 🗂️ Caching

Implements LRU caching with adaptive TTLs:

| Content Type | TTL |
|--------------|-----|
| Story lists | 5 min |
| Story details | 10 min |
| User info | 30 min |
| Search results | 3 min |
| Article content | 1 hour |

## 🔗 APIs Used

- [Algolia HN API](https://hn.algolia.com/api) - Fast search and story retrieval
- [Firebase HN API](https://github.com/HackerNews/API) - Official real-time API

## 🙏 Credits

- Original [mcp-hn](https://github.com/erithwik/mcp-hn) by [@erithwik](https://github.com/erithwik)
- Caching patterns from [karanb192/hn-mcp](https://github.com/karanb192/hn-mcp)
- Resource URI patterns from [paabloLC/mcp-hacker-news](https://github.com/paabloLC/mcp-hacker-news)
- Content extraction inspired by [GeorgeNance/hackernews-mcp](https://github.com/GeorgeNance/hackernews-mcp)
- Built with [FastMCP 3.0](https://gofastmcp.com/) by [@jlowin](https://github.com/jlowin)

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🔗 Links

- [PyPI Package](https://pypi.org/project/hn-mcp/)
- [GitHub Repository](https://github.com/machinemates-ai/hn-mcp)
- [FastMCP Documentation](https://gofastmcp.com/)
- [MCP Specification](https://modelcontextprotocol.io/)
