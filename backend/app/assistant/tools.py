"""Agent tools over the retrieval layer.

Every tool registers what it returns in the turn registry: only those chunks may be cited.
"""

import asyncio
import time
import uuid
from collections.abc import Callable

from pydantic_ai import RunContext

from app.assistant.deps import DocumentAgentDeps
from app.assistant.progress import report_progress
from app.assistant.status import emit_tool_start
from app.config import settings
from app.database.documents import get_chunks_by_ids, get_neighbor_chunks
from app.database.session import get_session
from app.retrieval.retriever import passage_from_chunk
from app.retrieval.types import (
    RetrievedPassage,
    SearchFilters,
    format_passages_for_agent,
)


def _read_chunks_sync(chunk_ids: list[uuid.UUID]) -> list[RetrievedPassage]:
    with get_session() as session:
        rows = get_chunks_by_ids(session, chunk_ids)
    return [passage_from_chunk(*rows[chunk_id], fusion_score=0.0) for chunk_id in chunk_ids if chunk_id in rows]


def _read_surrounding_sync(chunk_id: uuid.UUID, radius: int) -> list[RetrievedPassage]:
    with get_session() as session:
        rows = get_chunks_by_ids(session, [chunk_id])
        if chunk_id not in rows:
            return []
        anchor, document = rows[chunk_id]
        window = [*get_neighbor_chunks(session, [anchor], radius)[chunk_id], (anchor, document)]
    window.sort(key=lambda row: row[0].chunk_index)
    return [passage_from_chunk(chunk, chunk_document, fusion_score=0.0) for chunk, chunk_document in window]


async def _run_tool[T](deps: DocumentAgentDeps, name: str, detail: str, fn: Callable[[], T]) -> T:
    # Database and OpenAI calls are blocking; a worker thread keeps the event loop free,
    # so tool calls from one model response run concurrently.
    emit_tool_start(deps, name, detail)
    started = time.perf_counter()
    result = await asyncio.to_thread(fn)
    count = len(result) if isinstance(result, list) else 1
    report_progress(f"tool {name} done ({count} results) in {time.perf_counter() - started:.2f}s")
    return result


def _parse_ids(raw_ids: list[str]) -> list[uuid.UUID] | str:
    try:
        return [uuid.UUID(raw_id) for raw_id in raw_ids]
    except ValueError:
        return f"Error: chunk ids must be UUIDs copied from tool results, got {raw_ids!r}."


async def search_filings(
    ctx: RunContext[DocumentAgentDeps],
    query: str,
    ticker: str | None = None,
    form: str | None = None,
    fiscal_years: list[int] | None = None,
) -> str:
    """Hybrid (semantic + keyword) search over the filing corpus.

    Args:
        query: What to look for, in natural language.
        ticker: Company ticker in upper case, e.g. "AAPL".
        form: Filing form, e.g. "10-K".
        fiscal_years: Fiscal years to include, e.g. [2023, 2024].
    """
    filters = SearchFilters(ticker=ticker, form=form, fiscal_years=fiscal_years)
    detail = ", ".join(f"{key}={value}" for key, value in filters.model_dump(exclude_none=True).items())
    passages = await _run_tool(
        ctx.deps, "search_filings", detail, lambda: ctx.deps.retriever.search(query, filters=filters)
    )
    ctx.deps.registry.register(passages)
    return format_passages_for_agent(passages)


async def read_chunks(ctx: RunContext[DocumentAgentDeps], chunk_ids: list[str]) -> str:
    """Read the full text of several chunks in one call.

    Args:
        chunk_ids: Chunk ids exactly as shown in square brackets in earlier tool results.
    """
    ids = _parse_ids(chunk_ids)
    if isinstance(ids, str):
        return ids
    if not ids:
        return "Error: pass at least one chunk id."
    passages = await _run_tool(ctx.deps, "read_chunks", f"count={len(ids)}", lambda: _read_chunks_sync(ids))
    if not passages:
        return "Error: none of the requested chunks exist."
    ctx.deps.registry.register(passages)
    return format_passages_for_agent(passages, full_text=True)


async def read_chunk(ctx: RunContext[DocumentAgentDeps], chunk_id: str) -> str:
    """Read the full text of one chunk.

    Args:
        chunk_id: Chunk id exactly as shown in square brackets in an earlier tool result.
    """
    ids = _parse_ids([chunk_id])
    if isinstance(ids, str):
        return ids
    passages = await _run_tool(ctx.deps, "read_chunk", f"chunk_id={chunk_id}", lambda: _read_chunks_sync(ids))
    if not passages:
        return f"Error: chunk {chunk_id} does not exist."
    ctx.deps.registry.register(passages)
    return format_passages_for_agent(passages, full_text=True)


async def read_surrounding_chunks(
    ctx: RunContext[DocumentAgentDeps], chunk_id: str, radius: int | None = None
) -> str:
    """Read a chunk together with the chunks just before and after it in the same filing.

    Args:
        chunk_id: Chunk id exactly as shown in square brackets in an earlier tool result.
        radius: How many chunks to read on each side; defaults to 1.
    """
    ids = _parse_ids([chunk_id])
    if isinstance(ids, str):
        return ids
    radius = radius if radius is not None else settings.retrieval_neighbor_radius
    if radius < 1:
        return "Error: radius must be 1 or greater."
    passages = await _run_tool(
        ctx.deps,
        "read_surrounding_chunks",
        f"chunk_id={chunk_id} radius={radius}",
        lambda: _read_surrounding_sync(ids[0], radius),
    )
    if not passages:
        return f"Error: chunk {chunk_id} does not exist."
    ctx.deps.registry.register(passages)
    return format_passages_for_agent(passages, full_text=True)
