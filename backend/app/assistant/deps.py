"""Per-turn dependencies handed to the document agent and its tools."""

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field

from app.retrieval.retriever import DocumentRetriever
from app.retrieval.types import RetrievedPassage

StatusCallback = Callable[[str, str], None]  # (stage, message) shown to the analyst


@dataclass
class TurnRegistry:
    """Every chunk a tool returned during the turn: the only chunks the answer may cite."""

    passages_by_chunk_id: dict[uuid.UUID, RetrievedPassage] = field(default_factory=dict)

    def register(self, passages: list[RetrievedPassage]) -> None:
        for passage in passages:
            self.passages_by_chunk_id[passage.chunk_id] = passage
            # Neighbors were shown to the agent too, so they are citable.
            for neighbor in passage.neighbors:
                self.passages_by_chunk_id[neighbor.chunk_id] = neighbor


@dataclass
class DocumentAgentDeps:
    retriever: DocumentRetriever
    registry: TurnRegistry
    thread_id: uuid.UUID
    user_id: uuid.UUID
    on_status: StatusCallback | None = None

    def emit_status(self, stage: str, message: str) -> None:
        if self.on_status is not None:
            self.on_status(stage, message)
