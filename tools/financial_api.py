"""Mock financial data tool for research-agent development."""

from typing import Any


def get_financial_data(ticker: str) -> dict[str, Any]:
    """Return a clearly labelled mock financial-data response."""

    normalized_ticker = ticker.strip().upper()

    if not normalized_ticker:
        raise ValueError("Ticker must not be empty.")

    return {
        "ticker": normalized_ticker,
        "metrics": {},
        "data_source": "mock",
        "verified": False,
        "message": (
            "No live financial data was retrieved. "
            "Connect a financial data provider before using this tool "
            "for actual financial research."
        ),
    }
