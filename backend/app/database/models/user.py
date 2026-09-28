import uuid

from sqlalchemy.orm import Mapped, mapped_column

from app.database.models.base import Base, CreatedAt, UpdatedAt


class User(CreatedAt, UpdatedAt, Base):
    __tablename__ = "users"

    # Same value as auth.users.id, so it is set by the app instead of generated.
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True)
    display_name: Mapped[str | None]
