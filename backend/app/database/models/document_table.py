import uuid
from typing import Any

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models.base import Base, CreatedAt, UUIDPrimaryKey


class DocumentTable(UUIDPrimaryKey, CreatedAt, Base):
    """A financial table re-extracted from the filing's raw HTML.

    Docling's Markdown repeats colspan cells and splits "$"/"%" into their own cells,
    so tables are rebuilt from the HTML instead and stored here in clean form.
    """

    __tablename__ = "document_tables"
    __table_args__ = (UniqueConstraint("document_id", "table_index"),)

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_documents.id", ondelete="CASCADE"), index=True
    )
    # Position among the extracted tables of the filing, in document order.
    table_index: Mapped[int]
    title: Mapped[str | None]
    units: Mapped[str | None]
    markdown: Mapped[str]
    table_data: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    source_html_hash: Mapped[str]
