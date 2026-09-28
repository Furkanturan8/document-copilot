from typing import Any, Literal

from pydantic import BaseModel

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
