"""Hybrid retrieval: embed + keywords -> semantic and full-text search -> RRF -> hydrate + neighbors."""

from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.orm import Session

from app.config import settings
from app.database.documents import get_chunks_by_ids, get_neighbor_chunks
from app.database.models import DocumentChunk, SourceDocument
from app.database.session import get_session
from app.retrieval.embeddings import embed_query
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.keywords import extract_fts_keywords
from app.retrieval.queries import full_text_search, semantic_search
from app.retrieval.types import RankedChunkHit, RetrievedPassage, SearchFilters


class DocumentRetriever:
    def search(
        self,
        query: str,
        *,
        filters: SearchFilters | None = None,
        top_k: int | None = None,
        candidate_k: int | None = None,
        include_neighbors: bool = True,
    ) -> list[RetrievedPassage]:
        top_k = top_k or settings.retrieval_top_k
        candidate_k = candidate_k or settings.retrieval_candidate_k

        # Both prep steps are network calls to OpenAI, so they run side by side.
        with ThreadPoolExecutor(max_workers=2) as pool:
            query_vec = pool.submit(embed_query, query)
            fts_query = pool.submit(extract_fts_keywords, query, filters=filters)
            semantic_hits, fts_hits = _dual_search(
                query_vec.result(), fts_query.result(), candidate_k=candidate_k, filters=filters
            )

        fused = reciprocal_rank_fusion(
            [[hit.chunk_id for hit in semantic_hits], [hit.chunk_id for hit in fts_hits]],
            k=settings.retrieval_rrf_k,
        )[:top_k]
        if not fused:
            return []

        with get_session() as session:
            return _hydrate(session, fused, include_neighbors=include_neighbors)


def _dual_search(
    query_vec: list[float], fts_query: str, *, candidate_k: int, filters: SearchFilters | None
) -> tuple[list[RankedChunkHit], list[RankedChunkHit]]:
    """Run both search paths concurrently, each on its own session (a session is not thread-safe)."""

    def semantic() -> list[RankedChunkHit]:
        with get_session() as session:
            return semantic_search(session, query_vec, limit=candidate_k, filters=filters)

    def full_text() -> list[RankedChunkHit]:
        with get_session() as session:
            return full_text_search(session, fts_query, limit=candidate_k, filters=filters)

    with ThreadPoolExecutor(max_workers=2) as pool:
        semantic_future, full_text_future = pool.submit(semantic), pool.submit(full_text)
        return semantic_future.result(), full_text_future.result()


def _hydrate(session: Session, fused: list[tuple], *, include_neighbors: bool) -> list[RetrievedPassage]:
    """Load the fused chunks in fusion order, attaching each one's unseen neighbors."""
    rows = get_chunks_by_ids(session, [chunk_id for chunk_id, _ in fused])
    anchors = [rows[chunk_id][0] for chunk_id, _ in fused if chunk_id in rows]
    neighbors_by_anchor = (
        get_neighbor_chunks(session, anchors, settings.retrieval_neighbor_radius) if include_neighbors else {}
    )

    # A neighbor is shown once: not for a second hit, and not when it is a hit itself.
    seen = {chunk_id for chunk_id, _ in fused}
    passages: list[RetrievedPassage] = []
    for chunk_id, score in fused:
        if chunk_id not in rows:
            continue
        chunk, document = rows[chunk_id]
        neighbors = []
        for neighbor, neighbor_document in neighbors_by_anchor.get(chunk_id, []):
            if neighbor.id not in seen:
                seen.add(neighbor.id)
                neighbors.append(_passage(neighbor, neighbor_document, fusion_score=0.0))
        passages.append(_passage(chunk, document, fusion_score=score, neighbors=neighbors))
    return passages


def _passage(
    chunk: DocumentChunk,
    document: SourceDocument,
    *,
    fusion_score: float,
    neighbors: list[RetrievedPassage] | None = None,
) -> RetrievedPassage:
    return RetrievedPassage(
        chunk_id=chunk.id,
        document_id=chunk.document_id,
        chunk_index=chunk.chunk_index,
        text=chunk.content,
        page=chunk.page,
        section=chunk.section,
        fusion_score=fusion_score,
        ticker=document.ticker,
        company_name=document.company_name,
        form=document.filing_type,
        filing_date=document.filing_date,
        fiscal_year=document.fiscal_year,
        accession_number=document.accession_number,
        neighbors=neighbors or [],
    )
