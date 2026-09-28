import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models.base import Base, CreatedAt, UpdatedAt, UUIDPrimaryKey


class ChatThread(UUIDPrimaryKey, CreatedAt, UpdatedAt, Base):
    __tablename__ = "chat_threads"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(server_default="New chat")
