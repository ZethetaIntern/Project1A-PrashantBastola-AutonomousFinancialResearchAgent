"""Mock news sentiment tool for financial research."""

from typing import Any


def analyze_news_sentiment(
    ticker: str,
    headlines: list[str] | None = None,
) -> dict[str, Any]:
    """Return a transparent sentiment result for supplied headlines."""

    normalized_ticker = ticker.strip().upper()

    if not normalized_ticker:
        raise ValueError("Ticker must not be empty.")

    if headlines is None:
        headlines = []

    if not all(isinstance(item, str) for item in headlines):
        raise ValueError("Every headline must be a string.")

    if not headlines:
        sentiment = "unavailable"
        explanation = "No headlines were supplied; sentiment was not assessed."
    else:
        sentiment = "unassessed"
        explanation = (
            "Headlines were received, but no sentiment model has been "
            "connected. No positive or negative classification was made."
        )

    return {
        "ticker": normalized_ticker,
        "headlines": headlines,
        "headline_count": len(headlines),
        "sentiment": sentiment,
        "explanation": explanation,
        "data_source": "mock",
        "verified": False,
    }
