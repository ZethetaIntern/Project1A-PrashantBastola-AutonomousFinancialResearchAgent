"""Mock peer comparison tool for financial research."""

from typing import Any


def compare_peers(
    ticker: str,
    peer_tickers: list[str],
) -> dict[str, Any]:
    """Prepare a peer comparison without inventing financial metrics."""

    normalized_ticker = ticker.strip().upper()

    if not normalized_ticker:
        raise ValueError("Ticker must not be empty.")

    if not peer_tickers:
        raise ValueError("Provide at least one peer ticker.")

    normalized_peers = []
    for peer in peer_tickers:
        if not isinstance(peer, str) or not peer.strip():
            raise ValueError("Every peer ticker must be a non-empty string.")

        normalized_peers.append(peer.strip().upper())

    if normalized_ticker in normalized_peers:
        raise ValueError("The target company cannot also be listed as a peer.")

    return {
        "target_ticker": normalized_ticker,
        "peer_tickers": normalized_peers,
        "comparisons": [],
        "data_source": "mock",
        "verified": False,
        "message": (
            "No live peer financial metrics were retrieved. "
            "Connect a financial data provider before comparing performance."
        ),
    }
