
"""Retrieve reported earnings fundamentals using Yahoo Finance."""

from __future__ import annotations

import math
import threading
import time
from functools import lru_cache
from typing import Any

import pandas as pd
import yfinance as yf

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


def _number_or_none(value: Any) -> float | None:
    """Convert numeric values into finite JSON-safe floats."""
    if value is None or isinstance(value, bool):
        return None

    try:
        result = float(value)
    except (TypeError, ValueError):
        return None

    return result if math.isfinite(result) else None


@lru_cache(maxsize=128)
def _fetch_earnings(
    ticker: str,
    fiscal_period: str,
) -> dict[str, Any]:
    """Fetch annual or quarterly income-statement data."""
    _wait_for_rate_limit()

    normalized_period = fiscal_period.strip().lower()

    try:
        stock = yf.Ticker(ticker)

        if normalized_period in {"annual", "yearly"}:
            statement = stock.income_stmt
            period_type = "annual"

        elif normalized_period in {"quarterly", "quarter", "latest"}:
            statement = stock.quarterly_income_stmt
            period_type = "quarterly"

        elif (
            len(normalized_period) == 4
            and normalized_period.isdigit()
        ):
            # A four-digit year requests an annual statement.
            statement = stock.income_stmt
            period_type = "annual"

        else:
            # A full date requests a matching quarterly period.
            statement = stock.quarterly_income_stmt
            period_type = "quarterly"

        if statement is None or statement.empty:
            raise RuntimeError(
                f"No {period_type} income statement was available "
                f"for {ticker}."
            )

        available_periods = list(statement.columns)
        requested_date = None

        special_periods = {
            "latest", "annual", "yearly",
            "quarterly", "quarter",
        }

        if normalized_period not in special_periods:
            requested_date = pd.to_datetime(
                fiscal_period,
                errors="coerce",
            )

            if pd.isna(requested_date):
                raise ValueError(
                    "fiscal_period must be 'latest', 'annual', "
                    "'quarterly', a four-digit year, or a valid date."
                )

        selected_period = None

        for column in available_periods:
            period_date = pd.to_datetime(column, errors="coerce")

            if pd.isna(period_date):
                continue

            if requested_date is None:
                # Yahoo Finance normally orders columns newest first.
                selected_period = column
                break

            if (
                len(fiscal_period) == 4
                and fiscal_period.isdigit()
            ):
                if period_date.year == int(fiscal_period):
                    selected_period = column
                    break

            elif period_date.date() == requested_date.date():
                selected_period = column
                break

        if selected_period is None:
            raise RuntimeError(
                f"No matching {period_type} earnings period found "
                f"for {ticker} and period '{fiscal_period}'."
            )

        def find_value(*possible_names: str) -> float | None:
            """Find the first available statement metric."""
            for name in possible_names:
                if name not in statement.index:
                    continue

                value = statement.at[name, selected_period]

                if pd.notna(value):
                    return _number_or_none(value)

            return None

        return {
            "ticker": ticker,
            "fiscal_period_requested": fiscal_period,
            "period_type": period_type,
            "period_end": pd.to_datetime(
                selected_period
            ).date().isoformat(),
            "revenue": find_value(
                "Total Revenue",
                "Operating Revenue",
            ),
            "net_income": find_value("Net Income"),
            "operating_income": find_value("Operating Income"),
            "basic_eps": find_value("Basic EPS"),
            "data_source": "Yahoo Finance via yfinance",
            "verified": False,
            "message": (
                "Retrieved income-statement data from Yahoo Finance. "
                "Some fields may be unavailable. Verify important figures "
                "against company filings. This is not an earnings transcript."
            ),
        }

    except ValueError:
        raise
    except Exception as exc:
        raise RuntimeError(
            f"Could not retrieve earnings data for {ticker}: {exc}"
        ) from exc


def get_earnings(
    ticker: str,
    fiscal_period: str = "latest",
) -> dict[str, Any]:
    """Retrieve earnings data for a company and requested period."""
    if not isinstance(ticker, str) or not ticker.strip():
        raise ValueError("Ticker must not be empty.")

    if not isinstance(fiscal_period, str) or not fiscal_period.strip():
        raise ValueError("Fiscal period must not be empty.")

    normalized_ticker = ticker.strip().upper()
    normalized_period = fiscal_period.strip()

    if len(normalized_ticker) > 10:
        raise ValueError("Ticker must not exceed 10 characters.")

    if len(normalized_period) > 30:
        raise ValueError("Fiscal period must not exceed 30 characters.")

    result = _fetch_earnings(
        normalized_ticker,
        normalized_period,
    )

    return result
