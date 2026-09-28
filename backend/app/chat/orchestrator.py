"""One chat turn end to end: generate the assistant reply, stream it, then persist the turn."""

import asyncio
import uuid
from collections.abc import AsyncIterator
from typing import Any

import anyio
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


async def _persist_turn(
    client: AsyncClient, thread: dict[str, Any], user_message: UIMessage, assistant_message: UIMessage
) -> bool:
    # Shielded: on a client disconnect this runs inside a cancelled scope, where any
    # unshielded await would be cancelled immediately and the turn silently lost.
    with anyio.CancelScope(shield=True):
        try:
            await chats.append_turn(client, thread, user_message, assistant_message)
        except Exception:
            logger.exception("chat_turn_persist_failed", thread_id=thread["id"])
            return False
    return True


async def run_turn(
    client: AsyncClient,
    thread: dict[str, Any],
    user_message: UIMessage,
) -> AsyncIterator[str]:
    assistant_id = str(uuid.uuid4())
    text_id = str(uuid.uuid4())
    # The whole reply exists before streaming starts, so a disconnect mid-stream still
    # leaves a complete answer to store for the next history load.
    reply = _stub_reply(message_text(user_message))
    assistant_message = UIMessage(id=assistant_id, role="assistant", parts=[{"type": "text", "text": reply}])

    persisted = False
    try:
        yield streaming.start(assistant_id)
        yield streaming.text_start(text_id)
        for index, word in enumerate(reply.split(" ")):
            yield streaming.text_delta(text_id, word if index == 0 else " " + word)
            await asyncio.sleep(STUB_DELAY_SECONDS)
        yield streaming.text_end(text_id)
    finally:
        persisted = await _persist_turn(client, thread, user_message, assistant_message)

    if not persisted:
        # Headers are already sent, so an HTTP status is no longer possible; report the
        # failure in-band so the client shows an error instead of a silently unsaved reply.
        yield streaming.error("The reply could not be saved. Please try again.")
        yield streaming.DONE
        return

    yield streaming.finish()
    yield streaming.DONE
