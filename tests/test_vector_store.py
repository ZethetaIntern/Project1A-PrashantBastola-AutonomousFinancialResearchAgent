
from datetime import datetime, timezone

import pytest

from memory.vector_store import FinancialVectorStore


@pytest.fixture
def store(tmp_path):
    """Use an isolated temporary ChromaDB database for each test."""
    return FinancialVectorStore(persist_directory=tmp_path / "chroma")


def test_store_initializes_empty_collection(store):
    assert store.count() == 0


def test_add_and_get_record(store):
    record_id = store.add_record(
        content="Tesla reported increased automotive revenue.",
        ticker="TSLA",
        source_type="analysis",
        date=datetime(2024, 10, 15, tzinfo=timezone.utc),
        confidence=0.92,
        researcher_session="session-test-001",
        record_id="tsla-test-001",
    )

    record = store.get_record(record_id)

    assert record is not None
    assert record["id"] == "tsla-test-001"
    assert record["content"] == "Tesla reported increased automotive revenue."
    assert record["ticker"] == "TSLA"
    assert record["source_type"] == "analysis"
    assert record["confidence"] == pytest.approx(0.92)
    assert record["researcher_session"] == "session-test-001"
    assert store.count() == 1


def test_search_returns_relevant_record(store):
    store.add_record(
        content="Tesla reported strong electric vehicle deliveries.",
        ticker="TSLA",
        source_type="news",
        date="2024-10-15T00:00:00Z",
        confidence=0.9,
        researcher_session="session-test-002",
        record_id="tsla-news-001",
    )

    results = store.search("Tesla electric vehicle deliveries", ticker="TSLA")

    assert len(results) == 1
    assert results[0]["id"] == "tsla-news-001"


def test_invalid_confidence_is_rejected(store):
    with pytest.raises(ValueError, match="confidence"):
        store.add_record(
            content="Example financial finding.",
            ticker="TSLA",
            source_type="analysis",
            date="2024-10-15T00:00:00Z",
            confidence=1.5,
            researcher_session="session-test-003",
        )


def test_empty_content_is_rejected(store):
    with pytest.raises(ValueError, match="content"):
        store.add_record(
            content="   ",
            ticker="TSLA",
            source_type="analysis",
            date="2024-10-15T00:00:00Z",
            confidence=0.8,
            researcher_session="session-test-004",
        )


def test_unsupported_source_type_is_rejected(store):
    with pytest.raises(ValueError, match="source_type"):
        store.add_record(
            content="Example financial finding.",
            ticker="TSLA",
            source_type="unsupported",
            date="2024-10-15T00:00:00Z",
            confidence=0.8,
            researcher_session="session-test-005",
        )


def test_invalid_date_is_rejected(store):
    with pytest.raises(ValueError, match="date"):
        store.add_record(
            content="Example financial finding.",
            ticker="TSLA",
            source_type="analysis",
            date="not-a-date",
            confidence=0.8,
            researcher_session="session-test-006",
        )
