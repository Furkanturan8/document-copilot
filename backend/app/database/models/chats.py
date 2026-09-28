import uuid
from datetime import date
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models.base import Base, CreatedAt, UpdatedAt, UUIDPrimaryKey


class ChatThread(UUIDPrimaryKey, CreatedAt, UpdatedAt, Base):
    __tablename__ = "chat_threads"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(server_default="New chat")


class ChatMessage(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        CheckConstraint("role in ('user', 'assistant', 'system')", name="role_valid"),
        # Also serves as the thread_id index.
        UniqueConstraint("thread_id", "sequence"),
    )

    thread_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chat_threads.id", ondelete="CASCADE")
    )
    role: Mapped[str]
    content: Mapped[str]
    # Full AI SDK UIMessage, kept so history reloads render exactly as streamed.
    parts: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    # created_at can't order messages: now() is fixed per transaction, and a turn
    # writes the user and assistant messages together.
    sequence: Mapped[int]


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
