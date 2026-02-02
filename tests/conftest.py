"""
Pytest configuration for hn-mcp tests.

Following gemini-research-mcp patterns:
- Custom markers for test categorization
- Shared fixtures for test data
"""

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line("markers", "e2e: mark test as end-to-end (requires network)")
    config.addinivalue_line("markers", "slow: mark test as slow running")


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """Use asyncio for async tests."""
    return "asyncio"


@pytest.fixture
def sample_story() -> dict:
    """Sample HN story for testing."""
    return {
        "id": 1,
        "title": "Y Combinator",
        "url": "http://ycombinator.com",
        "author": "pg",
        "points": 57,
        "time": 1160418111,
        "num_comments": 15,
        "type": "story",
    }


@pytest.fixture
def sample_user() -> dict:
    """Sample HN user for testing."""
    return {
        "username": "pg",
        "karma": 156089,
        "created": 1160418092,
        "about": "Co-founder of Y Combinator.",
    }


@pytest.fixture
def sample_search_result() -> list[dict]:
    """Sample search results for testing."""
    return [
        {
            "id": 123,
            "title": "Python 4.0 Released",
            "url": "https://python.org/news",
            "author": "guido",
            "points": 1234,
        },
        {
            "id": 456,
            "title": "Learn Python in 2025",
            "url": "https://learnpython.org",
            "author": "coder",
            "points": 567,
        },
    ]
