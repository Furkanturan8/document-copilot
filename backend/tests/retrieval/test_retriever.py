import uuid
from contextlib import contextmanager
from datetime import date
from types import SimpleNamespace

from app.retrieval import retriever
from app.retrieval.types import RankedChunkHit

DOCUMENT_ID = uuid.uuid4()
DOCUMENT = SimpleNamespace(
    ticker="AAPL",
    company_name="Apple Inc.",
    filing_type="10-K",
    filing_date=date(2024, 11, 1),
    fiscal_year=2024,
    accession_number="0000320193-24-000123",
)


def chunk(index: int):
    return SimpleNamespace(
        id=uuid.uuid4(), document_id=DOCUMENT_ID, chunk_index=index, content=f"chunk {index}", page="23", section="Item 7"
    )


CHUNKS = [chunk(index) for index in range(6)]


def test_search_fuses_both_paths_and_attaches_unseen_neighbors(monkeypatch):
    by_id = {c.id: c for c in CHUNKS}
    # Semantic ranks chunks 1, 4; full text ranks 4, 2. Chunk 4 is in both lists, so it comes first.
    semantic = [RankedChunkHit(chunk_id=CHUNKS[1].id, rank=1), RankedChunkHit(chunk_id=CHUNKS[4].id, rank=2)]
    full_text = [RankedChunkHit(chunk_id=CHUNKS[4].id, rank=1), RankedChunkHit(chunk_id=CHUNKS[2].id, rank=2)]

    @contextmanager
    def fake_session():
        yield None

    def neighbors(_session, anchors, radius):
        return {
            anchor.id: [(c, DOCUMENT) for c in CHUNKS if c is not anchor and abs(c.chunk_index - anchor.chunk_index) <= radius]
            for anchor in anchors
        }

    monkeypatch.setattr(retriever, "embed_query", lambda _query: [0.0])
    monkeypatch.setattr(retriever, "extract_fts_keywords", lambda query, filters=None: query)
    monkeypatch.setattr(retriever, "get_session", fake_session)
    monkeypatch.setattr(retriever, "semantic_search", lambda *_args, **_kwargs: semantic)
    monkeypatch.setattr(retriever, "full_text_search", lambda *_args, **_kwargs: full_text)
    monkeypatch.setattr(retriever, "get_chunks_by_ids", lambda _s, ids: {i: (by_id[i], DOCUMENT) for i in ids})
    monkeypatch.setattr(retriever, "get_neighbor_chunks", neighbors)

    passages = retriever.DocumentRetriever().search("revenue mix", top_k=3)

    assert [p.chunk_index for p in passages] == [4, 1, 2]
    assert passages[0].fusion_score > passages[1].fusion_score
    # Neighbors of 4 are 3 and 5; neighbors of 1 are 0 and 2, but 2 is itself a hit.
    assert [n.chunk_index for n in passages[0].neighbors] == [3, 5]
    assert [n.chunk_index for n in passages[1].neighbors] == [0]
    assert passages[2].neighbors == []
    assert passages[0].form == "10-K" and passages[0].text == "chunk 4"
