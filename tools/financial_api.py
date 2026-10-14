
"""Live financial data retrieval using Yahoo Finance via yfinance."""

from __future__ import annotations

import threading
import time
from functools import lru_cache
from typing import Any

import yfinance as yf

from config.settings import TOOL_TIMEOUT_SECONDS

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
def _fetch_financial_data(ticker: str) -> dict[str, Any]:
    """Fetch and cache a company's current financial information."""
    _wait_for_rate_limit()

    try:
        stock = yf.Ticker(ticker)

        # yfinance does not consistently expose a configurable HTTP
        # timeout through Ticker.history/info. These calls can therefore
        # take longer than TOOL_TIMEOUT_SECONDS.
        info = stock.info
        history = stock.history(period="5d", timeout=TOOL_TIMEOUT_SECONDS)

    except Exception as exc:
        raise RuntimeError(
            f"Yahoo Finance request failed for {ticker}: {exc}"
        ) from exc

    if not info and history.empty:
        raise RuntimeError(
            f"Yahoo Finance returned no usable data for {ticker}."
        )

    def number_or_none(value: Any) -> float | None:
        """Convert finite numeric values to JSON-safe floats."""
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            import math

            result = float(value)
            return result if math.isfinite(result) else None
        return None

    latest_close = (
        number_or_none(history["Close"].dropna().iloc[-1])
        if not history.empty and not history["Close"].dropna().empty
        else None
    )

    previous_close = (
        number_or_none(history["Close"].dropna().iloc[-2])
        if not history.empty and len(history["Close"].dropna()) >= 2
        else None
    )

    change_percent = None
    if (
        latest_close is not None
        and previous_close is not None
        and previous_close != 0
    ):
        change_percent = (
            (latest_close - previous_close) / previous_close
        ) * 100

    metrics = {
        "company_name": info.get("longName") or info.get("shortName"),
        "currency": info.get("currency"),
        "exchange": info.get("exchange"),
        "current_price": number_or_none(
            info.get("currentPrice")
            or info.get("regularMarketPrice")
            or latest_close
        ),
        "latest_close": latest_close,
        "previous_close": previous_close,
        "daily_change_percent": number_or_none(change_percent),
        "market_cap": info.get("marketCap"),
        "trailing_pe": number_or_none(info.get("trailingPE")),
        "forward_pe": number_or_none(info.get("forwardPE")),
        "price_to_book": number_or_none(info.get("priceToBook")),
        "dividend_yield": number_or_none(info.get("dividendYield")),
        "fifty_two_week_high": number_or_none(info.get("fiftyTwoWeekHigh")),
        "fifty_two_week_low": number_or_none(info.get("fiftyTwoWeekLow")),
    }

    return {
        "metrics": metrics,
        "data_source": "Yahoo Finance via yfinance",
        "verified": True,
        "message": (
            "Retrieved live provider data. Values may be delayed or missing; "
            "verify important figures against primary sources."
        ),
    }


def get_financial_data(ticker: str) -> dict[str, Any]:
    """Retrieve financial metrics for a company ticker."""
    normalized_ticker = ticker.strip().upper()

    if not normalized_ticker:
        raise ValueError("Ticker must not be empty.")

    result = _fetch_financial_data(normalized_ticker)

    return {
        "ticker": normalized_ticker,
        **result,
    }
