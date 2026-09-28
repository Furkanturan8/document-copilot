"""One chat turn end to end: generate the assistant reply, stream it, then persist the turn."""

import asyncio
import uuid
from collections.abc import AsyncIterator
from typing import Any

import structlog
from supabase import AsyncClient

from app.chat import streaming
from app.chat.messages import UIMessage, message_text
from app.database import chats

logger = structlog.get_logger()

STUB_DELAY_SECONDS = 0.03


def _stub_reply(question: str) -> str:
    # Placeholder until retrieval and the PydanticAI agent replace it.
    return f'This is a stubbed reply; grounded answers arrive in a later phase. You asked: "{question}"'


async def run_turn(
    client: AsyncClient,
    thread: dict[str, Any],
    user_message: UIMessage,
) -> AsyncIterator[str]:
    assistant_id = str(uuid.uuid4())
    text_id = str(uuid.uuid4())
    reply = _stub_reply(message_text(user_message))

    yield streaming.start(assistant_id)
    yield streaming.text_start(text_id)
    for index, word in enumerate(reply.split(" ")):
        yield streaming.text_delta(text_id, word if index == 0 else " " + word)
        await asyncio.sleep(STUB_DELAY_SECONDS)
    yield streaming.text_end(text_id)

    # Persisted only after the full reply was generated; a client disconnect cancels this
    # generator before here, so half-finished turns are never stored.
    assistant_message = UIMessage(id=assistant_id, role="assistant", parts=[{"type": "text", "text": reply}])
    try:
        await chats.append_turn(client, thread, user_message, assistant_message)
    except Exception:
        # Headers are already sent, so an HTTP status is no longer possible; report the
        # failure in-band so the client shows an error instead of a silently unsaved reply.
        logger.exception("chat_turn_persist_failed", thread_id=thread["id"])
        yield streaming.error("The reply could not be saved. Please try again.")
        yield streaming.DONE
        return

    yield streaming.finish()
    yield streaming.DONE
