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


def _excerpt(text: str) -> str:
    text = text.strip()
    return text[:MAX_PASSAGE_EXCERPT_CHARS] + "..." if len(text) > MAX_PASSAGE_EXCERPT_CHARS else text


def _format_passage(passage: RetrievedPassage) -> str:
    page = f" p.{passage.page}" if passage.page else ""
    section = f" ({passage.section})" if passage.section else ""
    header = f"{passage.ticker} {passage.form} FY{passage.fiscal_year}{page}{section} [{passage.chunk_id}]"
    lines = [f"{header}: {_excerpt(passage.text)}"]
    lines += [
        f"  neighbor idx={neighbor.chunk_index} [{neighbor.chunk_id}]: {_excerpt(neighbor.text)}"
        for neighbor in passage.neighbors
    ]
    return "\n".join(lines)


def format_passages_for_agent(passages: list[RetrievedPassage]) -> str:
    """Bounded, grep-style text for agent tool responses; ids let the agent cite a chunk."""
    if not passages:
        return "No matching passages found in the filing corpus."
    output = "\n\n".join(_format_passage(passage) for passage in passages)
    if len(output) > MAX_AGENT_OUTPUT_CHARS:
        output = output[:MAX_AGENT_OUTPUT_CHARS] + f"\n... truncated ({len(passages)} passages)."
    return output
