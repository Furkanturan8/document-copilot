"""Structured output of the document agent."""

import uuid

from pydantic import BaseModel, Field


class Citation(BaseModel):
    citation_index: int = Field(description="1-based number used as [n] in the answer text")
    chunk_id: uuid.UUID = Field(description="Id of the retrieved chunk that supports the claim")
    excerpt: str = Field(description="Text copied verbatim from that chunk")


class GroundedAnswer(BaseModel):
    answer: str = Field(description="Answer text with [n] citation markers")
    citations: list[Citation] = Field(default_factory=list, description="One entry per [n] marker in the answer")
    insufficient_evidence: bool = Field(
        default=False, description="True when the retrieved passages cannot support an answer"
    )
