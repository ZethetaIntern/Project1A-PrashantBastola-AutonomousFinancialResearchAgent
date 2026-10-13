
"""Persistent ChromaDB vector store for financial research memory."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import logging
import uuid

import chromadb

from config.settings import CHROMA_PERSIST_DIRECTORY

logger = logging.getLogger(__name__)

COLLECTION_NAME = "financial_research"
VALID_SOURCE_TYPES = {
    "10-K",
    "10-Q",
    "8-K",
    "earnings_call",
    "news",
    "analysis",
}


class FinancialVectorStore:
    """Store and retrieve financial research findings using ChromaDB."""

    def __init__(self, persist_directory: str | Path | None = None) -> None:
        directory = Path(
            persist_directory or CHROMA_PERSIST_DIRECTORY
        ).expanduser()

        if not directory.is_absolute():
            directory = Path(__file__).resolve().parent.parent / directory

        directory.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(path=str(directory))
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"description": "Financial research findings"},
        )

        logger.info(
            "Vector store initialized: collection=%s, path=%s",
            COLLECTION_NAME,
            directory,
        )

    @staticmethod
    def _validate_record(
        content: str,
        ticker: str,
        source_type: str,
        confidence: float,
        researcher_session: str,
    ) -> None:
        if not content.strip():
            raise ValueError("content must not be empty")
        if not ticker.strip():
            raise ValueError("ticker must not be empty")
        if source_type not in VALID_SOURCE_TYPES:
            raise ValueError(
                f"source_type must be one of {sorted(VALID_SOURCE_TYPES)}"
            )
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if not researcher_session.strip():
            raise ValueError("researcher_session must not be empty")

    def add_record(
        self,
        content: str,
        ticker: str,
        source_type: str,
        date: str | datetime,
        confidence: float,
        researcher_session: str,
        record_id: str | None = None,
    ) -> str:
        """Validate and persist one finding; Chroma generates its embedding."""
        self._validate_record(
            content, ticker, source_type, confidence, researcher_session
        )

        if isinstance(date, datetime):
            source_date = date
        else:
            try:
                source_date = datetime.fromisoformat(
                    date.replace("Z", "+00:00")
                )
            except (ValueError, AttributeError) as exc:
                raise ValueError(
                    "date must be an ISO-8601 date or datetime"
                ) from exc

        if source_date.tzinfo is None:
            source_date = source_date.replace(tzinfo=timezone.utc)

        source_date = source_date.astimezone(timezone.utc)
        identifier = record_id or str(uuid.uuid4())

        self.collection.upsert(
            ids=[identifier],
            documents=[content],
            metadatas=[
                {
                    "ticker": ticker.upper().strip(),
                    "source_type": source_type,
                    "date": source_date.isoformat(),
                    "confidence": float(confidence),
                    "researcher_session": researcher_session.strip(),
                }
            ],
        )

        logger.info(
            "Financial finding stored: id=%s ticker=%s source_type=%s",
            identifier,
            ticker.upper().strip(),
            source_type,
        )
        return identifier

    def search(
        self,
        query: str,
        n_results: int = 5,
        ticker: str | None = None,
        source_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Find semantically similar findings, optionally filtering metadata."""
        if not query.strip():
            raise ValueError("query must not be empty")
        if n_results < 1:
            raise ValueError("n_results must be at least 1")

        filters: list[dict[str, Any]] = []
        if ticker:
            filters.append({"ticker": ticker.upper().strip()})
        if source_type:
            if source_type not in VALID_SOURCE_TYPES:
                raise ValueError("Unsupported source_type")
            filters.append({"source_type": source_type})

        where = None
        if len(filters) == 1:
            where = filters[0]
        elif len(filters) > 1:
            where = {"$and": filters}

        result = self.collection.query(
            query_texts=[query],
            n_results=min(n_results, max(1, self.collection.count())),
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        records: list[dict[str, Any]] = []
        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        for identifier, document, metadata, distance in zip(
            ids, documents, metadatas, distances
        ):
            records.append(
                {
                    "id": identifier,
                    "content": document,
                    "embedding": None,
                    "ticker": metadata["ticker"],
                    "source_type": metadata["source_type"],
                    "date": metadata["date"],
                    "confidence": metadata["confidence"],
                    "researcher_session": metadata["researcher_session"],
                    "distance": distance,
                }
            )

        logger.info(
            "Vector search completed: results=%d ticker=%s",
            len(records),
            ticker or "all",
        )
        return records

    def get_record(self, record_id: str) -> dict[str, Any] | None:
        """Retrieve a stored finding by its ID."""
        result = self.collection.get(
            ids=[record_id],
            include=["documents", "metadatas"],
        )

        if not result["ids"]:
            return None

        return {
            "id": result["ids"][0],
            "content": result["documents"][0],
            **result["metadatas"][0],
            "embedding": None,
        }

    def count(self) -> int:
        """Return the number of stored findings."""
        return self.collection.count()
