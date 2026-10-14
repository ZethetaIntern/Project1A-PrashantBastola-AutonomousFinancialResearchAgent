"""Retrieve financial news with Tavily and estimate sentiment with TextBlob."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from tavily import TavilyClient
from textblob import TextBlob

from config.settings import TOOL_TIMEOUT_SECONDS, WEB_SEARCH_API_KEY


def _score_headlines(headlines: list[str]) -> dict[str, Any]:
    """Estimate sentiment using TextBlob polarity."""
    scores = [
        TextBlob(headline).sentiment.polarity
        for headline in headlines
        if headline.strip()
    ]

    if not scores:
        return {
            "sentiment": "unavailable",
            "average_polarity": None,
            "explanation": "No usable headlines were available to score.",
        }

    average = sum(scores) / len(scores)

    if average > 0.1:
        sentiment = "positive"
    elif average < -0.1:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    return {
        "sentiment": sentiment,
        "average_polarity": round(average, 4),
        "explanation": (
            f"TextBlob estimated {sentiment} sentiment across "
            f"{len(scores)} headline(s). This is a basic lexical estimate, "
            "not a financial recommendation."
        ),
    }


@lru_cache(maxsize=128)
def _fetch_news(ticker: str) -> tuple[dict[str, str], ...]:
    """Fetch and cache financial news results from Tavily."""
    if not WEB_SEARCH_API_KEY:
        raise RuntimeError("WEB_SEARCH_API_KEY is not configured.")

    client = TavilyClient(api_key=WEB_SEARCH_API_KEY)
    response = client.search(
        query=f"{ticker} stock financial news earnings revenue",
        topic="news",
        max_results=10,
        search_depth="basic",
        timeout=TOOL_TIMEOUT_SECONDS,
    )

    articles = []
    for result in response.get("results", []):
        title = result.get("title")
        if not isinstance(title, str) or not title.strip():
            continue

        url = result.get("url", "")
        articles.append({
            "title": title.strip(),
            "url": url,
            "source": url,
            "published_at": result.get("published_date") or "",
        })

    return tuple(articles)


def analyze_news_sentiment(
    ticker: str,
    headlines: list[str] | None = None,
) -> dict[str, Any]:
    """Analyze supplied headlines or fetch news and score sentiment."""
    if not isinstance(ticker, str) or not ticker.strip():
        raise ValueError("Ticker must not be empty.")

    normalized_ticker = ticker.strip().upper()
    if len(normalized_ticker) > 10:
        raise ValueError("Ticker must not exceed 10 characters.")

    if headlines is not None and (
        not isinstance(headlines, list)
        or not all(isinstance(item, str) for item in headlines)
    ):
        raise ValueError("Headlines must be a list of strings.")

    if headlines:
        selected_headlines = [
            item.strip() for item in headlines if item.strip()
        ]
        articles = []
        data_source = "User-supplied headlines"
    else:
        articles = list(_fetch_news(normalized_ticker))
        selected_headlines = [article["title"] for article in articles]
        data_source = "Tavily News Search API"

    scored = _score_headlines(selected_headlines)

    return {
        "ticker": normalized_ticker,
        "headlines": selected_headlines,
        "articles": articles,
        "headline_count": len(selected_headlines),
        **scored,
        "data_source": data_source,
        "verified": False,
        "message": (
            "Sentiment is estimated from headlines. News claims and sentiment "
            "labels have not been independently verified."
        ),
    }
