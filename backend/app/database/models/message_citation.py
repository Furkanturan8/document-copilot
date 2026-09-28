import uuid
from datetime import date

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models.base import Base, CreatedAt, UUIDPrimaryKey


class MessageCitation(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "message_citations"
    __table_args__ = (UniqueConstraint("message_id", "citation_index"),)

    message_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chat_messages.id", ondelete="CASCADE"), index=True
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_chunks.id", ondelete="RESTRICT"), index=True
    )
    citation_index: Mapped[int]
    # Snapshot of the cited passage and its filing so old answers stay verifiable
    # after re-chunking, and the UI can render citations without joins.
    excerpt: Mapped[str]
    ticker: Mapped[str]
    company_name: Mapped[str | None]
    filing_type: Mapped[str]
    filing_date: Mapped[date]
    page: Mapped[str | None]
    section: Mapped[str | None]
