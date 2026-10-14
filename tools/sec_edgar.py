
"""SEC EDGAR full-text filing search with caching and rate limiting."""

from __future__ import annotations

import threading
import time
from functools import lru_cache
from typing import Any
from urllib.parse import urlencode

import httpx

from config.settings import SEC_USER_AGENT, TOOL_TIMEOUT_SECONDS

SEC_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"
ALLOWED_FILING_TYPES = {"10-K", "10-Q", "8-K"}

# Keep SEC requests spaced apart across concurrent tool calls.
_rate_lock = threading.Lock()
_last_request_at = 0.0
_MIN_REQUEST_INTERVAL = 0.25  # At most 4 requests/second in this process.


def _wait_for_rate_limit() -> None:
    """Space out SEC requests to avoid sending them too quickly."""
    global _last_request_at

    with _rate_lock:
        now = time.monotonic()
        wait = _MIN_REQUEST_INTERVAL - (now - _last_request_at)

        if wait > 0:
            time.sleep(wait)

        _last_request_at = time.monotonic()


@lru_cache(maxsize=128)
def _search_cached(
    ticker: str, filing_type: str, limit: int
) -> dict[str, Any]:
    """Fetch and cache SEC full-text search results."""
    if not SEC_USER_AGENT.strip():
        raise RuntimeError(
            "SEC_USER_AGENT is missing. Set it in your local .env file "
            "to identify your application and provide a contact email."
        )

    params = {
        "q": ticker,
        "forms": filing_type,
        "dateRange": "custom",
        "startdt": "2000-01-01",
        "enddt": time.strftime("%Y-%m-%d", time.gmtime()),
        "from": 0,
        "size": limit,
    }

    _wait_for_rate_limit()

    try:
        with httpx.Client(
            timeout=TOOL_TIMEOUT_SECONDS,
            headers={
                "User-Agent": SEC_USER_AGENT,
                "Accept": "application/json",
            },
        ) as client:
            response = client.get(
                SEC_SEARCH_URL,
                params=params,
            )
            response.raise_for_status()
            payload = response.json()

    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"SEC EDGAR returned HTTP {exc.response.status_code}."
        ) from exc
    except httpx.RequestError as exc:
        raise RuntimeError(
            f"Could not reach SEC EDGAR: {exc}"
        ) from exc
    except ValueError as exc:
        raise RuntimeError(
            "SEC EDGAR returned invalid JSON."
        ) from exc


    hits = payload.get("hits", {}).get("hits", [])
    results = []
    seen = set()
    ticker_upper = ticker.upper()

    for hit in hits:
        source = hit.get("_source", {})
        companies = source.get("display_names", [])
        company_text = " ".join(companies).upper()

        # Keep results associated with the requested ticker/company.
        if ticker_upper not in company_text:
            continue

        accession = source.get("adsh")
        form = source.get("form")

        # Remove duplicates and amendment forms such as 10-K/A.
        if not accession or accession in seen or form != filing_type:
            continue

        seen.add(accession)

        results.append({
            "company": companies,
            "form": form,
            "filing_date": source.get("file_date"),
            "accession_number": accession,
            "file_url": source.get("file_url"),
            "description": source.get("display_date"),
        })

        if len(results) >= limit:
            break

    return {
        "results": results,
        "result_count": len(results),
        "data_source": "SEC EDGAR full-text search",
        "verified": True,
        "query_url": f"{SEC_SEARCH_URL}?{urlencode(params)}",
    }


def search_sec_filings(
    ticker: str,
    filing_type: str = "10-K",
    max_results: int = 10,
) -> dict[str, Any]:
    """Search SEC EDGAR filings for a ticker or company name."""
    normalized_ticker = ticker.strip().upper()
    normalized_type = filing_type.strip().upper()

    if not normalized_ticker:
        raise ValueError("Ticker or company name must not be empty.")

    if normalized_type not in ALLOWED_FILING_TYPES:
        raise ValueError(
            f"Unsupported filing type {normalized_type!r}. "
            f"Choose from {sorted(ALLOWED_FILING_TYPES)}."
        )

    if not 1 <= max_results <= 50:
        raise ValueError("max_results must be between 1 and 50.")

    result = _search_cached(
        normalized_ticker,
        normalized_type,
        max_results,
    )

    return {
        "ticker": normalized_ticker,
        "filing_type": normalized_type,
        **result,
    }
