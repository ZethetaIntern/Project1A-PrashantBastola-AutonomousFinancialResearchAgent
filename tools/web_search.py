
"""Live web search for financial research using Tavily."""

from __future__ import annotations

import threading
import time
from functools import lru_cache
from typing import Any

from tavily import TavilyClient

from config.settings import TOOL_TIMEOUT_SECONDS, WEB_SEARCH_API_KEY

_rate_lock = threading.Lock()
_last_request_at = 0.0
_MIN_REQUEST_INTERVAL = 1.0


def _wait_for_rate_limit() -> None:
    """Space out requests made by this process."""
    global _last_request_at

    with _rate_lock:
        now = time.monotonic()
        wait = _MIN_REQUEST_INTERVAL - (now - _last_request_at)

        if wait > 0:
            time.sleep(wait)

        _last_request_at = time.monotonic()


@lru_cache(maxsize=128)
def _search_cached(query: str, max_results: int) -> dict[str, Any]:
    """Fetch and cache normalized Tavily search results."""
    if not WEB_SEARCH_API_KEY.strip():
        raise RuntimeError(
            "WEB_SEARCH_API_KEY is missing. Configure it in your local .env file."
        )

    _wait_for_rate_limit()

    try:
        client = TavilyClient(api_key=WEB_SEARCH_API_KEY)
        response = client.search(
            query=query,
            max_results=max_results,
            search_depth="basic",
            timeout=TOOL_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        raise RuntimeError(f"Tavily web search failed: {exc}") from exc

    results = []
    for item in response.get("results", []):
        results.append({
            "title": item.get("title"),
            "url": item.get("url"),
            "content": item.get("content"),
            "score": item.get("score"),
            "published_date": item.get("published_date"),
        })

    return {
        "results": results,
        "result_count": len(results),
        "data_source": "Tavily Search API",
        "verified": True,
        "message": (
            "Live search results retrieved. Verify important claims against "
            "their original sources."
        ),
    }


def search_web(query: str, max_results: int = 5) -> dict[str, Any]:
    """Search the web and return normalized results."""
    normalized_query = query.strip()

    if not normalized_query:
        raise ValueError("Search query must not be empty.")

    if not 1 <= max_results <= 10:
        raise ValueError("max_results must be between 1 and 10.")

    return {
        "query": normalized_query,
        "max_results": max_results,
        **_search_cached(normalized_query, max_results),
    }
