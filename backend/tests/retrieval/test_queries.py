import uuid
from types import SimpleNamespace

from app.retrieval.queries import (
    build_filters,
    full_text_search,
    full_text_sql,
    semantic_search,
    semantic_sql,
)
from app.retrieval.types import SearchFilters


class RecordingSession:
    """Stands in for a SQLAlchemy session: records the SQL and returns canned rows."""

    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def execute(self, statement, params):
        self.calls.append((str(statement), params))
        return SimpleNamespace(all=lambda: self.rows)


def test_no_filters_add_no_sql():
    assert build_filters(None).sql == ""
    assert build_filters(SearchFilters()).sql == ""


def test_filters_are_anded_and_bound_as_parameters():
    clause = build_filters(SearchFilters(ticker="AAPL", fiscal_years=[2023, 2024], form="10-K"))
    assert clause.sql == " AND sd.ticker = :ticker AND sd.fiscal_year = ANY(:fiscal_years) AND sd.filing_type = :form"
    assert clause.params == {"ticker": "AAPL", "fiscal_years": [2023, 2024], "form": "10-K"}


def test_semantic_sql_orders_by_cosine_distance():
    sql = semantic_sql(" AND sd.ticker = :ticker")
    assert "ORDER BY dc.embedding <=> CAST(:query_vec AS vector)" in sql
    assert "WHERE dc.embedding IS NOT NULL AND sd.ticker = :ticker" in sql


def test_full_text_sql_uses_plainto_tsquery_and_search_vector():
    sql = full_text_sql("")
    assert "plainto_tsquery(CAST(:fts_config AS regconfig), :query_text)" in sql
    assert "dc.search_vector @@ query" in sql


def test_semantic_search_sends_vector_literal_and_ranks_from_one():
    first, second = uuid.uuid4(), uuid.uuid4()
    session = RecordingSession([SimpleNamespace(id=first, score=0.9), SimpleNamespace(id=second, score=0.5)])
    hits = semantic_search(session, [0.1, 0.2], limit=5, filters=SearchFilters(ticker="NVDA"))

    _, params = session.calls[0]
    assert params["query_vec"] == "[0.1,0.2]"
    assert params["limit"] == 5 and params["ticker"] == "NVDA"
    assert [(hit.chunk_id, hit.rank) for hit in hits] == [(first, 1), (second, 2)]


def test_full_text_search_passes_config_and_query_text():
    session = RecordingSession([])
    assert full_text_search(session, "iPhone net sales", limit=50) == []
    _, params = session.calls[0]
    assert params["query_text"] == "iPhone net sales"
    assert params["fts_config"] == "english"
