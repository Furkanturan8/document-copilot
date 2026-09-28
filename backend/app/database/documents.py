"""Read queries over source documents and their chunks."""

import uuid

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.database.models import DocumentChunk, SourceDocument

ChunkWithDocument = tuple[DocumentChunk, SourceDocument]


def get_chunks_by_ids(session: Session, chunk_ids: list[uuid.UUID]) -> dict[uuid.UUID, ChunkWithDocument]:
    if not chunk_ids:
        return {}
    rows = session.execute(
        select(DocumentChunk, SourceDocument)
        .join(SourceDocument, SourceDocument.id == DocumentChunk.document_id)
        .where(DocumentChunk.id.in_(chunk_ids))
    ).tuples()
    return {chunk.id: (chunk, document) for chunk, document in rows}


def get_neighbor_chunks(
    session: Session, anchors: list[DocumentChunk], radius: int
) -> dict[uuid.UUID, list[ChunkWithDocument]]:
    """Chunks within `radius` indices of each anchor in the same document, keyed by anchor id.

    One query for all anchors: each round trip to Supabase costs hundreds of milliseconds.
    """
    if not anchors or radius <= 0:
        return {anchor.id: [] for anchor in anchors}
    windows = [
        and_(
            DocumentChunk.document_id == anchor.document_id,
            DocumentChunk.chunk_index.between(anchor.chunk_index - radius, anchor.chunk_index + radius),
        )
        for anchor in anchors
    ]
    rows = session.execute(
        select(DocumentChunk, SourceDocument)
        .join(SourceDocument, SourceDocument.id == DocumentChunk.document_id)
        .where(or_(*windows))
        .order_by(DocumentChunk.document_id, DocumentChunk.chunk_index)
    ).tuples()
    candidates = list(rows)
    return {
        anchor.id: [
            (chunk, document)
            for chunk, document in candidates
            if chunk.document_id == anchor.document_id
            and chunk.id != anchor.id
            and abs(chunk.chunk_index - anchor.chunk_index) <= radius
        ]
        for anchor in anchors
    }
