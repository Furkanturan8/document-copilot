import uuid
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models.base import Base, CreatedAt, UUIDPrimaryKey


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
