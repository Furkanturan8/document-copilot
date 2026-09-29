import uuid
from dataclasses import dataclass
from datetime import date

import anyio

from app.assistant import tools
from app.assistant.deps import DocumentAgentDeps, TurnRegistry
from app.retrieval.types import (
    MAX_PASSAGE_EXCERPT_CHARS,
    RetrievedPassage,
    SearchFilters,
)


def _passage(text: str = "Data Center revenue increased.", **overrides) -> RetrievedPassage:
    fields = {
        "chunk_id": uuid.uuid4(),
        "document_id": uuid.uuid4(),
        "chunk_index": 3,
        "text": text,
        "page": "42",
        "section": "Item 7",
        "fusion_score": 0.0,
        "ticker": "NVDA",
        "company_name": "NVIDIA Corporation",
        "form": "10-K",
        "filing_date": date(2024, 2, 21),
        "fiscal_year": 2024,
        "accession_number": "0001045810-24-000029",
    }
    return RetrievedPassage(**(fields | overrides))


class FakeRetriever:
    def __init__(self, passages: list[RetrievedPassage]):
        self.passages = passages
        self.calls: list[tuple[str, SearchFilters | None]] = []

    def search(self, query, *, filters=None):
        self.calls.append((query, filters))
        return self.passages


@dataclass
class FakeContext:
    deps: DocumentAgentDeps


def _context(retriever=None) -> FakeContext:
    deps = DocumentAgentDeps(
        retriever=retriever or FakeRetriever([]),
        registry=TurnRegistry(),
        thread_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
    )
    return FakeContext(deps)


def test_search_filings_registers_hits_and_their_neighbors():
    neighbor = _passage("Next chunk.")
    hit = _passage(neighbors=[neighbor])
    retriever = FakeRetriever([hit])
    ctx = _context(retriever)

    output = anyio.run(lambda: tools.search_filings(ctx, "data center", ticker="NVDA", fiscal_years=[2024]))

    assert set(ctx.deps.registry.passages_by_chunk_id) == {hit.chunk_id, neighbor.chunk_id}
    assert retriever.calls == [("data center", SearchFilters(ticker="NVDA", fiscal_years=[2024]))]
    assert str(hit.chunk_id) in output


def test_search_filings_reports_status_with_filters():
    statuses = []
    ctx = _context()
    ctx.deps.on_status = lambda stage, message: statuses.append((stage, message))

    anyio.run(lambda: tools.search_filings(ctx, "capex", ticker="MSFT"))

    assert statuses == [("searching", "Searching SEC filings… (ticker=MSFT)")]


def test_read_chunks_returns_full_text(monkeypatch):
    long_text = "word " * 400
    passage = _passage(long_text)
    monkeypatch.setattr(tools, "_read_chunks_sync", lambda ids: [passage])
    ctx = _context()

    output = anyio.run(lambda: tools.read_chunks(ctx, [str(passage.chunk_id)]))

    assert len(long_text.strip()) > MAX_PASSAGE_EXCERPT_CHARS
    assert long_text.strip() in output
    assert passage.chunk_id in ctx.deps.registry.passages_by_chunk_id


def test_read_chunks_rejects_invalid_ids_without_querying(monkeypatch):
    def fail(ids):
        raise AssertionError("must not query")

    monkeypatch.setattr(tools, "_read_chunks_sync", fail)
    ctx = _context()

    output = anyio.run(lambda: tools.read_chunks(ctx, ["chunk-1"]))

    assert output.startswith("Error:")
    assert not ctx.deps.registry.passages_by_chunk_id


def test_read_chunk_missing_chunk_is_an_error_and_registers_nothing(monkeypatch):
    monkeypatch.setattr(tools, "_read_chunks_sync", lambda ids: [])
    ctx = _context()

    output = anyio.run(lambda: tools.read_chunk(ctx, str(uuid.uuid4())))

    assert output.startswith("Error:")
    assert not ctx.deps.registry.passages_by_chunk_id


def test_read_surrounding_chunks_rejects_zero_radius():
    ctx = _context()

    output = anyio.run(lambda: tools.read_surrounding_chunks(ctx, str(uuid.uuid4()), radius=0))

    assert output == "Error: radius must be 1 or greater."
