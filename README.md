# HN-MCP 🔥

[![PyPI](https://img.shields.io/pypi/v/hn-mcp)](https://pypi.org/project/hn-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/hn-mcp)](https://pypi.org/project/hn-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-51%20passing-brightgreen)](https://github.com/machinemates-ai/hn-mcp)

**Access Hacker News through AI.** A production-ready [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) server that gives LLMs real-time access to Hacker News stories, comments, users, and article content.

Built with [FastMCP 2.x](https://gofastmcp.com/) for modern async performance.

> **Forked from [erithwik/mcp-hn](https://github.com/erithwik/mcp-hn)** — Enhanced with FastMCP 2.x, async httpx, intelligent caching, MCP Resources/Prompts, and secure article extraction using trafilatura.

---

## Why HN-MCP?

| What You Get | Why It Matters |
|-------------|----------------|
| **Real-time tech pulse** | Access HN's curated feed of what matters in tech right now |
| **Community signals** | 500k+ active users voting/commenting = real developer sentiment |
| **Historical search** | 10+ years of tech discussions via Algolia (instant) |
| **Full article content** | Read linked articles without leaving your AI workflow |
| **Sub-second responses** | Async + caching = 50-500ms typical latency |

### What Makes HN-MCP Different

- **6 Tools** — Stories, search, users, article extraction, cache stats
- **7 Resources** — `hackernews://` URIs for direct feed access
- **2 Prompts** — Pre-built templates for summarization and analysis
- **Dual APIs** — Algolia for search, Firebase for real-time data
- **Smart Caching** — Adaptive TTLs per content type (5min → 1hr)
- **Secure Extraction** — trafilatura (F1: 0.937) with full SSRF protection
- **51 Tests** — Unit + E2E with live API verification

---

## Perfect For

| User | Use Case |
|------|----------|
| **Founders** | "What's HN saying about my competitor's launch?" |
| **Recruiters** | "Find active HN users who work on [technology]" |
| **Content Creators** | "What topics are trending this week?" |
| **Researchers** | "Analyze sentiment on AI developments over time" |
| **Developers** | "What are people saying about this new framework?" |
| **Investors** | "Track reaction to funding announcements" |

---

## Installation

```bash
# Using uv (recommended)
uv pip install hn-mcp

# Using pip
pip install hn-mcp

# From source
git clone https://github.com/machinemates-ai/hn-mcp
cd hn-mcp
uv sync
```

### Requirements

- Python 3.10+
- No API keys required (HN APIs are free and public)

---

## Quick Start

### CLI

```bash
# Start the MCP server
hn-mcp

# Or with Python module
python -m hn_mcp
```

### Programmatic

```python
from hn_mcp import mcp

if __name__ == "__main__":
    mcp.run()
```

### Test with FastMCP Client

```python
import asyncio
from hn_mcp import mcp
from fastmcp import Client

async def test():
    async with Client(mcp) as client:
        result = await client.call_tool("get_stories", {"story_type": "top", "num_stories": 5})
        print(result.content[0].text)

asyncio.run(test())
```

---

## MCP Client Configuration

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "hn": {
      "command": "uvx",
      "args": ["hn-mcp"]
    }
  }
}
```

### VS Code with GitHub Copilot

Add to `.vscode/mcp.json` (workspace) or user settings:

```json
{
  "servers": {
    "hn": {
      "type": "stdio",
      "command": "uvx",
      "args": ["hn-mcp"]
    }
  }
}
```

### Cursor

Add to MCP configuration:

```json
{
  "hn": {
    "command": "uvx",
    "args": ["hn-mcp"]
  }
}
```

### Cline

Add to MCP settings:

```json
{
  "mcpServers": {
    "hn": {
      "command": "uvx",
      "args": ["hn-mcp"]
    }
  }
}
```

---

## Tools

All tools include `ToolAnnotations(readOnlyHint=True)` for MCP 2025-03-26 compliance.

| Tool | Description | Typical Latency |
|------|-------------|-----------------|
| `get_stories` | Get stories by type (top, new, best, ask, show, job) | 100-300ms |
| `search_stories` | Full-text search via Algolia with date sorting | 50-200ms |
| `get_story_info` | Story details with threaded comments | 200-500ms |
| `get_user_info` | User profile, karma, and submissions | 150-400ms |
| `fetch_article_content` | Extract article as Markdown (trafilatura) | 500ms-2s |
| `cache_stats` | View cache hit/miss statistics | <10ms |

### Tool Parameters

#### `get_stories`
```python
get_stories(
    story_type: str = "top",  # top, new, best, ask, show, job
    num_stories: int = 10     # 1-500
)
```

#### `search_stories`
```python
search_stories(
    query: str,               # Search terms
    num_results: int = 10,    # 1-1000
    search_by_date: bool = False  # Sort by date vs relevance
)
```

#### `get_story_info`
```python
get_story_info(
    story_id: int,                # HN item ID
    include_comments: bool = True,
    comment_depth: int = 3        # 1-10
)
```

#### `get_user_info`
```python
get_user_info(
    user_name: str,          # HN username
    num_stories: int = 5     # Recent submissions to include
)
```

#### `fetch_article_content`
```python
fetch_article_content(
    url: str  # URL to extract (SSRF-protected)
)
```

---

## Resources

Access HN data directly via URI:

| URI | Description |
|-----|-------------|
| `hackernews://top` | Front page stories (≈30) |
| `hackernews://new` | Newest submissions |
| `hackernews://best` | Highest-voted all-time |
| `hackernews://ask` | Ask HN threads |
| `hackernews://show` | Show HN projects |
| `hackernews://jobs` | YC job postings |
| `hackernews://story/{id}` | Story with comments |
| `hackernews://user/{username}` | User profile |

---

## Prompts

Pre-built templates for common workflows:

| Prompt | Arguments | Description |
|--------|-----------|-------------|
| `summarize_hn` | `num_stories` | Summarize top N stories |
| `analyze_discussion` | `story_id` | Deep analysis of comment thread |

---

## Real-World Examples

### "What's trending on HN today?"

```
User: What are the top stories on Hacker News right now?

→ Tool: get_stories(story_type="top", num_stories=10)

AI: Here are today's top stories:
1. "Why SQLite is taking over" - 847 points, 312 comments
2. "Show HN: I built a neural network in Excel" - 623 points
...
```

### "Research a topic"

```
User: What has HN discussed about LangChain in the past year?

→ Tool: search_stories(query="LangChain", num_results=20, search_by_date=True)

AI: I found 20 recent discussions about LangChain...
- Most upvoted: "Why we switched from LangChain to..." (423 pts)
- Common themes: complexity concerns, alternatives like...
```

### "Analyze a discussion"

```
User: Can you summarize the discussion on story 41234567?

→ Tool: get_story_info(story_id=41234567, include_comments=True, comment_depth=5)

AI: This story about [topic] has 234 comments. Key themes:
- 40% of commenters argue that...
- Notable dissent from user 'expert123' who...
```

### "Read an article"

```
User: Can you read the article from story 41234567?

→ Tool: get_story_info(story_id=41234567)
→ Tool: fetch_article_content(url="https://example.com/article")

AI: The article argues that... [full summary based on extracted content]
```

### "Research a user"

```
User: Tell me about pg on Hacker News

→ Tool: get_user_info(user_name="pg", num_stories=10)

AI: Paul Graham (@pg) is the founder of Hacker News with:
- Karma: 157,316 points
- Member since: 2006
- Recent activity: Posted "Show HN: Bel" about his new Lisp...
```

---

## Caching

Intelligent LRU caching with content-aware TTLs:

| Content Type | TTL | Rationale |
|--------------|-----|-----------|
| Story lists | 5 min | Front page changes frequently |
| Story details | 10 min | Comments accumulate over time |
| User info | 30 min | Profiles rarely change |
| Search results | 3 min | New content constantly indexed |
| Article content | 1 hour | Articles don't change |

Check cache performance:

```python
→ Tool: cache_stats()

{
  "total_items": 47,
  "hit_rate": "73.2%",
  "by_type": {
    "stories_list": {"items": 12, "hits": 89, "misses": 23},
    "article_content": {"items": 8, "hits": 45, "misses": 8}
  }
}
```

---

## Rate Limits

HN-MCP uses two APIs with different rate limits:

| API | Rate Limit | Notes |
|-----|------------|-------|
| **Algolia HN API** | ~10,000 req/hour | Used for `search_stories` |
| **Firebase HN API** | ~200 req/min | Used for `get_stories`, `get_story_info`, `get_user_info` |

With caching enabled, typical usage stays well under these limits. The cache dramatically reduces API calls for repeated queries.

---

## Security

### SSRF Protection

`fetch_article_content` blocks requests to:

- **Private IPv4**: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`
- **Private IPv6**: `::1`, `fc00::/7`, `fe80::/10`
- **Cloud metadata**: `169.254.169.254`, `metadata.google.internal`
- **Internal hosts**: `localhost`, `*.local`, `*.internal`

### Content Extraction

Uses [trafilatura](https://trafilatura.readthedocs.io/) for safe HTML→Markdown conversion:

- No JavaScript execution
- Sanitized output
- Timeout protection (10s max)
- Maximum 5MB response size

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HN_CACHE_ENABLED` | `true` | Enable/disable caching |
| `HN_CACHE_MAX_SIZE` | `1000` | Maximum items per cache type |
| `HN_REQUEST_TIMEOUT` | `10` | HTTP timeout in seconds |
| `HN_LOG_LEVEL` | `INFO` | Logging verbosity |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FastMCP Server                        │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Tools (6)  │  Resources (7)  │  Prompts (2)            │ │
│  └─────────────────────────────────────────────────────────┘ │
│                              │                                │
│  ┌───────────────────────────┴───────────────────────────┐  │
│  │                   Cache Layer (LRU)                    │  │
│  │    stories_list │ story_detail │ user_info │ search    │  │
│  └───────────────────────────────────────────────────────┘  │
│                              │                                │
│  ┌───────────────────────────┴───────────────────────────┐  │
│  │                    HTTP Layer (httpx)                  │  │
│  │                     Async + Pooled                     │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
          ▼                    ▼                    ▼
   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
   │  Algolia    │     │  Firebase   │     │  Web URLs   │
   │  HN API     │     │  HN API     │     │ (articles)  │
   │  (search)   │     │  (items)    │     │ trafilatura │
   └─────────────┘     └─────────────┘     └─────────────┘
```

---

## Development

### Setup

```bash
git clone https://github.com/machinemates-ai/hn-mcp
cd hn-mcp
uv sync --all-extras
```

### Testing

```bash
# Run all tests
uv run pytest

# Unit tests only (fast, mocked)
uv run pytest tests/test_unit.py -v

# E2E tests (live API calls)
uv run pytest tests/test_e2e.py -v -m e2e

# With coverage
uv run pytest --cov=hn_mcp --cov-report=html
```

### Code Quality

```bash
# Format
uv run ruff format .

# Lint
uv run ruff check .

# Type check
uv run mypy src/
```

---

## Troubleshooting

### "Tool not found" error

Ensure you're using the correct tool names:
- `get_stories` (not `get_story`)
- `get_story_info` (not `get_story`)
- `get_user_info` (not `get_user`)

### "Connection timeout" errors

```bash
# Increase timeout
export HN_REQUEST_TIMEOUT=30
```

### High API usage

Check cache stats to ensure caching is working:
```
→ cache_stats()
```

If hit rate is low, verify `HN_CACHE_ENABLED=true`.

### Article extraction fails

Some sites block automated access. Common issues:
- Paywalled content → Returns error message
- JavaScript-only sites → Partial content
- Rate-limited domains → 429 errors

### "SSRF blocked" error

This is expected for internal/private URLs. The server won't fetch:
- `localhost`, `127.0.0.1`
- Private IP ranges
- Cloud metadata endpoints

---

## Comparison with Alternatives

| Feature | HN-MCP | [karanb192/hn-mcp](https://github.com/karanb192/hn-mcp) | [erithwik/mcp-hn](https://github.com/erithwik/mcp-hn) |
|---------|--------|-------------------|------------------|
| Language | Python | TypeScript | Python |
| Framework | FastMCP 2.x | MCP SDK | MCP SDK |
| Async | ✅ httpx | ✅ fetch | ❌ requests |
| Caching | ✅ LRU+TTL | ✅ LRU+TTL | ❌ |
| Resources | ✅ 7 | ❌ | ❌ |
| Prompts | ✅ 2 | ❌ | ❌ |
| Article extraction | ✅ trafilatura | ❌ | ❌ |
| SSRF protection | ✅ Full | N/A | ❌ |
| Tests | 51 | Unknown | 0 |

---

## APIs Used

| API | Endpoint | Used For |
|-----|----------|----------|
| [Algolia HN](https://hn.algolia.com/api) | `hn.algolia.com/api/v1` | `search_stories` — fast full-text search |
| [Firebase HN](https://github.com/HackerNews/API) | `hacker-news.firebaseio.com/v0` | `get_stories`, `get_story_info`, `get_user_info` — official real-time |

---

## Credits

- **Original fork**: [erithwik/mcp-hn](https://github.com/erithwik/mcp-hn) by [@erithwik](https://github.com/erithwik)
- **Caching patterns**: [karanb192/hn-mcp](https://github.com/karanb192/hn-mcp)
- **Resource URIs**: [paabloLC/mcp-hacker-news](https://github.com/paabloLC/mcp-hacker-news)
- **Content extraction**: [GeorgeNance/hackernews-mcp](https://github.com/GeorgeNance/hackernews-mcp)
- **FastMCP**: [jlowin/fastmcp](https://github.com/jlowin/fastmcp) by [@jlowin](https://github.com/jlowin)
- **trafilatura**: [adbar/trafilatura](https://github.com/adbar/trafilatura) by [@adbar](https://github.com/adbar)

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Links

- **PyPI**: [pypi.org/project/hn-mcp](https://pypi.org/project/hn-mcp/)
- **GitHub**: [github.com/machinemates-ai/hn-mcp](https://github.com/machinemates-ai/hn-mcp)
- **FastMCP Docs**: [gofastmcp.com](https://gofastmcp.com/)
- **MCP Spec**: [modelcontextprotocol.io](https://modelcontextprotocol.io/)
- **HN API Docs**: [github.com/HackerNews/API](https://github.com/HackerNews/API)
