from datetime import date, datetime

from sqlalchemy import DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

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
    # Deferred: up to ~1 MB per filing, so it loads only when explicitly accessed.
    content_markdown: Mapped[str | None] = mapped_column(deferred=True)
    # Set only after all chunks and embeddings are written; re-runs skip documents where it is set.
    ingested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
