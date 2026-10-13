"""Mock web search tool for financial research."""

from typing import Any


def search_web(query: str, max_results: int = 5) -> dict[str, Any]:
    """Return a structured mock web-search response."""

    if not query.strip():
        raise ValueError("Search query must not be empty.")

    if not 1 <= max_results <= 10:
        raise ValueError("max_results must be between 1 and 10.")

    return {
        "query": query.strip(),
        "max_results": max_results,
        "results": [],
        "result_count": 0,
        "data_source": "mock",
        "verified": False,
        "message": (
            "Mock implementation only. No live web search "
            "has been performed."
        ),
    }
