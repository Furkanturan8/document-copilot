from typing import Any, Literal

from pydantic import BaseModel

from app.assistant.deps import TurnRegistry
from app.assistant.outputs import Citation, GroundedAnswer
from app.retrieval.types import RetrievedPassage

DEFAULT_THREAD_TITLE = "New chat"
TITLE_MAX_LENGTH = 60


class UIMessage(BaseModel):
    """AI SDK UIMessage as sent by the frontend and returned for history reloads.

    Parts stay untyped dicts: the backend only reads text parts, and storing the rest
    verbatim keeps history rendering identical to what was streamed.
    """

    id: str
    role: Literal["user", "assistant", "system"]
    parts: list[dict[str, Any]]


def message_text(message: UIMessage) -> str:
    return "".join(part.get("text", "") for part in message.parts if part.get("type") == "text")


def title_from_text(text: str) -> str:
    title = " ".join(text.split())
    if len(title) <= TITLE_MAX_LENGTH:
        return title or DEFAULT_THREAD_TITLE
    return title[: TITLE_MAX_LENGTH - 1].rstrip() + "…"


def row_to_ui_message(row: dict[str, Any]) -> UIMessage:
    parts = row["parts"] or [{"type": "text", "text": row["content"]}]
    return UIMessage(id=str(row["id"]), role=row["role"], parts=parts)


def citation_part(citation: Citation, passage: RetrievedPassage) -> dict[str, Any]:
    """A `data-citation` part: the citation plus a snapshot of its passage's filing, so the
    UI can render it without another request."""
    return {
        "type": "data-citation",
        "id": f"citation-{citation.citation_index}",
        "data": {
            "citationIndex": citation.citation_index,
            "chunkId": str(citation.chunk_id),
            "excerpt": citation.excerpt,
            "ticker": passage.ticker,
            "companyName": passage.company_name,
            "form": passage.form,
            "filingDate": passage.filing_date.isoformat(),
            "fiscalYear": passage.fiscal_year,
            "page": passage.page,
            "section": passage.section,
        },
    }


def build_assistant_message(message_id: str, answer: GroundedAnswer, registry: TurnRegistry) -> UIMessage:
    """Only for validated answers: every citation's chunk is then in the registry."""
    parts: list[dict[str, Any]] = [{"type": "text", "text": answer.answer}]
    parts += [
        citation_part(citation, registry.passages_by_chunk_id[citation.chunk_id]) for citation in answer.citations
    ]
    return UIMessage(id=message_id, role="assistant", parts=parts)
