import uuid
from datetime import date, datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Computed, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.config import settings
from app.database.models.base import Base, CreatedAt, UpdatedAt, UUIDPrimaryKey


class SourceDocument(UUIDPrimaryKey, CreatedAt, UpdatedAt, Base):
    __tablename__ = "source_documents"
    __table_args__ = (Index("ix_source_documents_ticker_fiscal_year", "ticker", "fiscal_year"),)

    ticker: Mapped[str]
    cik: Mapped[str]
    company_name: Mapped[str | None]
    filing_type: Mapped[str]
    filing_date: Mapped[date]
    report_date: Mapped[date]
    fiscal_year: Mapped[int]
    accession_number: Mapped[str] = mapped_column(unique=True)
    primary_document: Mapped[str]
    source_url: Mapped[str]
    content_markdown: Mapped[str | None]
    # Set only after all chunks and embeddings are written; re-runs skip documents where it is set.
    ingested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DocumentChunk(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index"),
        Index(
            "ix_document_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index(
            "ix_document_chunks_search_vector_gin",
            "search_vector",
            postgresql_using="gin",
        ),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_documents.id", ondelete="CASCADE"), index=True
    )
    chunk_index: Mapped[int]
    section: Mapped[str | None]
    # Filing page labels are not always numeric (e.g. "F-3").
    page: Mapped[str | None]
    content: Mapped[str]
    token_count: Mapped[int]
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(settings.openai_embedding_dimensions)
    )
    search_vector: Mapped[str] = mapped_column(
        TSVECTOR, Computed("to_tsvector('english', content)", persisted=True)
    )
    # "metadata" is reserved on declarative classes, hence the attribute rename.
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, server_default="{}"
    )
