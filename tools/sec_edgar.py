
from typing import Any


def search_sec_filings(
    ticker: str,
    filing_type: str = "10-K",
) -> dict[str, Any]:
    """Return clearly labelled mock filing-search results."""

    normalized_ticker = ticker.strip().upper()
    normalized_type = filing_type.strip().upper()

    if not normalized_ticker:
        raise ValueError("Ticker must not be empty.")

    allowed_types = {"10-K", "10-Q", "8-K"}
    if normalized_type not in allowed_types:
        raise ValueError(
            f"Unsupported filing type. Choose one of {sorted(allowed_types)}."
        )

    return {
        "ticker": normalized_ticker,
        "filing_type": normalized_type,
        "results": [],
        "result_count": 0,
        "data_source": "mock",
        "message": (
            "Mock implementation only. No live SEC EDGAR search "
            "has been performed."
        ),
    }
