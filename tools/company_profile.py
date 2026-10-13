
"""Mock company profile tool for financial research."""

from typing import Any


MOCK_COMPANIES: dict[str, dict[str, Any]] = {
    "MSFT": {
        "company_name": "Microsoft Corporation",
        "ticker": "MSFT",
        "sector": "Technology",
        "industry": "Software",
        "description": "A technology company focused on software, cloud services, and AI.",
        "data_source": "mock",
    },
    "AAPL": {
        "company_name": "Apple Inc.",
        "ticker": "AAPL",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "description": "A technology company focused on consumer devices and services.",
        "data_source": "mock",
    },
    "TSLA": {
        "company_name": "Tesla, Inc.",
        "ticker": "TSLA",
        "sector": "Automotive",
        "industry": "Electric Vehicles",
        "description": "An electric vehicle and clean energy company.",
        "data_source": "mock",
    },
}


def get_company_profile(ticker: str) -> dict[str, Any]:
    """Return a mock profile for a supported ticker."""
    normalized_ticker = ticker.strip().upper()

    if not normalized_ticker:
        raise ValueError("Ticker cannot be empty.")

    if normalized_ticker not in MOCK_COMPANIES:
        raise ValueError(
            f"No mock profile available for ticker: {normalized_ticker}"
        )

    # Return a copy so callers cannot modify the stored mock data.
    return dict(MOCK_COMPANIES[normalized_ticker])
