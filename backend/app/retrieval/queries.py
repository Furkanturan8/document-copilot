"""The two search paths over document_chunks: pgvector semantic search and Postgres full-text."""

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.retrieval.types import RankedChunkHit, SearchFilters


@dataclass(frozen=True)
class FilterClause:
    sql: str
    params: dict[str, object]


def build_filters(filters: SearchFilters | None) -> FilterClause:
    clauses: list[str] = []
    params: dict[str, object] = {}
    if filters and filters.ticker:
        clauses.append("sd.ticker = :ticker")
        params["ticker"] = filters.ticker
    if filters and filters.fiscal_years:
        clauses.append("sd.fiscal_year = ANY(:fiscal_years)")
        params["fiscal_years"] = filters.fiscal_years
    if filters and filters.form:
        clauses.append("sd.filing_type = :form")
        params["form"] = filters.form
    return FilterClause("".join(f" AND {clause}" for clause in clauses), params)


def semantic_sql(filter_sql: str) -> str:
    # <=> is pgvector's cosine distance, which the HNSW index is built for; similarity = 1 - distance.
    return f"""
        SELECT dc.id, 1 - (dc.embedding <=> CAST(:query_vec AS vector)) AS score
        FROM document_chunks dc
        JOIN source_documents sd ON sd.id = dc.document_id
        WHERE dc.embedding IS NOT NULL{filter_sql}
        ORDER BY dc.embedding <=> CAST(:query_vec AS vector)
        LIMIT :limit
    """


def full_text_sql(filter_sql: str) -> str:
    # plainto_tsquery ANDs every word, so the query text should be a few focused keywords.
    return f"""
        SELECT dc.id, ts_rank_cd(dc.search_vector, query) AS score
        FROM document_chunks dc
        JOIN source_documents sd ON sd.id = dc.document_id,
             plainto_tsquery(CAST(:fts_config AS regconfig), :query_text) AS query
        WHERE dc.search_vector @@ query{filter_sql}
        ORDER BY score DESC
        LIMIT :limit
    """


def _to_hits(rows: list) -> list[RankedChunkHit]:
    return [RankedChunkHit(chunk_id=row.id, rank=rank, score=row.score) for rank, row in enumerate(rows, start=1)]


def semantic_search(
    session: Session, query_vec: list[float], *, limit: int, filters: SearchFilters | None = None
) -> list[RankedChunkHit]:
    clause = build_filters(filters)
    params = {"query_vec": "[" + ",".join(map(str, query_vec)) + "]", "limit": limit, **clause.params}
    return _to_hits(session.execute(text(semantic_sql(clause.sql)), params).all())


def full_text_search(
    session: Session, query_text: str, *, limit: int, filters: SearchFilters | None = None
) -> list[RankedChunkHit]:
    clause = build_filters(filters)
    params = {
        "query_text": query_text,
        "fts_config": settings.retrieval_fts_config,
        "limit": limit,
        **clause.params,
    }
    return _to_hits(session.execute(text(full_text_sql(clause.sql)), params).all())
