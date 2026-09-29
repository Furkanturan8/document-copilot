"""Models shared by retrieval and the agent tools that call it."""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, Field

MAX_PASSAGE_EXCERPT_CHARS = 800
MAX_AGENT_OUTPUT_CHARS = 12_000


class SearchFilters(BaseModel):
    """Optional filters, ANDed together; an unset field filters nothing."""

    ticker: str | None = None
    fiscal_years: list[int] | None = None
    form: str | None = None


class RankedChunkHit(BaseModel):
    chunk_id: uuid.UUID
    rank: int  # 1-based position in its own result list
    score: float | None = None


class RetrievedPassage(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    text: str
    page: str | None
    section: str | None
    fusion_score: float  # 0.0 for neighbors, which were not ranked themselves
    ticker: str
    company_name: str | None
    form: str
    filing_date: date
    fiscal_year: int
    accession_number: str
    neighbors: list[RetrievedPassage] = Field(default_factory=list)


def _excerpt(text: str, *, full_text: bool) -> str:
    text = text.strip()
    if full_text or len(text) <= MAX_PASSAGE_EXCERPT_CHARS:
        return text
    return text[:MAX_PASSAGE_EXCERPT_CHARS] + "..."


def _format_passage(passage: RetrievedPassage, *, full_text: bool) -> str:
    page = f" p.{passage.page}" if passage.page else ""
    section = f" ({passage.section})" if passage.section else ""
    header = f"{passage.ticker} {passage.form} FY{passage.fiscal_year}{page}{section} [{passage.chunk_id}]"
    lines = [f"{header}: {_excerpt(passage.text, full_text=full_text)}"]
    lines += [
        f"  neighbor idx={neighbor.chunk_index} [{neighbor.chunk_id}]: {_excerpt(neighbor.text, full_text=full_text)}"
        for neighbor in passage.neighbors
    ]
    return "\n".join(lines)


def format_passages_for_agent(passages: list[RetrievedPassage], *, full_text: bool = False) -> str:
    """Bounded, grep-style text for agent tool responses; ids let the agent cite a chunk.

    Search results show excerpts. Read tools pass full_text=True: the agent must see the
    whole chunk to quote it, so passages are then kept whole or left out, never cut.
    """
    if not passages:
        return "No matching passages found in the filing corpus."
    if not full_text:
        output = "\n\n".join(_format_passage(passage, full_text=False) for passage in passages)
        if len(output) > MAX_AGENT_OUTPUT_CHARS:
            output = output[:MAX_AGENT_OUTPUT_CHARS] + f"\n... truncated ({len(passages)} passages)."
        return output

    blocks: list[str] = []
    left_out: list[str] = []
    size = 0
    for passage in passages:
        block = _format_passage(passage, full_text=True)
        if blocks and size + len(block) > MAX_AGENT_OUTPUT_CHARS:
            left_out.append(str(passage.chunk_id))
            continue
        blocks.append(block)
        size += len(block) + 2
    if left_out:
        blocks.append(f"... {len(left_out)} passages left out to stay within the size limit; read them separately: {', '.join(left_out)}")
    return "\n\n".join(blocks)
