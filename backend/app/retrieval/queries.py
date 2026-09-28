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
    # Iterative scans may return candidates slightly out of order, so the materialized CTE
    # collects them and the outer query re-sorts. "+ 0" matters: without it Postgres trusts the
    # CTE's ORDER BY and skips the sort (as the pgvector docs recommend).
    return f"""
        WITH candidates AS MATERIALIZED (
            SELECT dc.id, dc.embedding <=> CAST(:query_vec AS vector) AS distance
            FROM document_chunks dc
            JOIN source_documents sd ON sd.id = dc.document_id
            WHERE dc.embedding IS NOT NULL{filter_sql}
            ORDER BY distance
            LIMIT :limit
        )
        SELECT id, 1 - distance AS score FROM candidates ORDER BY distance + 0
    """


# An HNSW scan stops after hnsw.ef_search (default 40) candidates and only then applies the
# WHERE filters, so a ticker-filtered search could return 3 hits instead of 50. Iterative
# scans (pgvector >= 0.8) keep walking the index until enough rows pass the filters.
# set_config(..., true) is SET LOCAL: it lasts until the end of the current transaction.
ITERATIVE_SCAN_SQL = """
    SELECT set_config('hnsw.iterative_scan', 'relaxed_order', true),
           set_config('hnsw.ef_search', CAST(:ef_search AS text), true)
"""


def full_text_sql(filter_sql: str) -> str:
    # plainto_tsquery normalizes the keywords (stemming, stop words) but ANDs them, and five
    # ANDed keywords matched nothing for 3 of 10 test questions. Its '&'s become '|' so any
    # keyword matches; chunks matching more distinct keywords rank first, then ts_rank_cd.
    return f"""
        WITH q AS (
            SELECT CAST(replace(CAST(plainto_tsquery(CAST(:fts_config AS regconfig), :query_text) AS text),
                                '&', '|') AS tsquery) AS query,
                   tsvector_to_array(to_tsvector(CAST(:fts_config AS regconfig), :query_text)) AS terms
        )
        SELECT dc.id,
               (SELECT count(*) FROM unnest(q.terms) AS term
                WHERE dc.search_vector @@ CAST(quote_literal(term) AS tsquery)) AS matched_terms,
               ts_rank_cd(dc.search_vector, q.query) AS score
        FROM document_chunks dc
        JOIN source_documents sd ON sd.id = dc.document_id, q
        WHERE dc.search_vector @@ q.query{filter_sql}
        ORDER BY matched_terms DESC, score DESC
        LIMIT :limit
    """


def _to_hits(rows: list) -> list[RankedChunkHit]:
    return [RankedChunkHit(chunk_id=row.id, rank=rank, score=row.score) for rank, row in enumerate(rows, start=1)]


def semantic_search(
    session: Session, query_vec: list[float], *, limit: int, filters: SearchFilters | None = None
) -> list[RankedChunkHit]:
    clause = build_filters(filters)
    session.execute(text(ITERATIVE_SCAN_SQL), {"ef_search": max(limit, 40)})
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
