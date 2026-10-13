"""Mock earnings information tool for financial research."""

from typing import Any


def get_earnings(
    ticker: str,
    fiscal_period: str = "latest",
) -> dict[str, Any]:
    """Return a clearly labelled mock earnings response."""

    normalized_ticker = ticker.strip().upper()
    normalized_period = fiscal_period.strip()

    if not normalized_ticker:
        raise ValueError("Ticker must not be empty.")

    if not normalized_period:
        raise ValueError("Fiscal period must not be empty.")

    return {
        "ticker": normalized_ticker,
        "fiscal_period": normalized_period,
        "revenue": None,
        "net_income": None,
        "earnings_transcript": None,
        "data_source": "mock",
        "verified": False,
        "message": (
            "No live earnings data or transcript was retrieved. "
            "Connect an earnings data provider to populate these fields."
        ),
    }
