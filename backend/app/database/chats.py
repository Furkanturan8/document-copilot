"""Chat thread and message persistence.

Functions take a user-scoped client unless noted, so RLS backs up every query.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from supabase import AsyncClient

from app.chat.messages import (
    DEFAULT_THREAD_TITLE,
    UIMessage,
    message_text,
    row_to_ui_message,
    title_from_text,
)

THREAD_COLUMNS = "id,user_id,title,created_at,updated_at"


async def get_thread(service_client: AsyncClient, thread_id: uuid.UUID) -> dict[str, Any] | None:
    # Service role on purpose: under RLS another user's thread is indistinguishable from a
    # missing one, and the API must answer 403 rather than 404 for it.
    response = await (
        service_client.table("chat_threads").select(THREAD_COLUMNS).eq("id", str(thread_id)).limit(1).execute()
    )
    return response.data[0] if response.data else None


async def list_threads(client: AsyncClient, user_id: uuid.UUID) -> list[dict[str, Any]]:
    response = await (
        client.table("chat_threads")
        .select(THREAD_COLUMNS)
        .eq("user_id", str(user_id))
        .order("updated_at", desc=True)
        .execute()
    )
    return response.data


async def create_thread(client: AsyncClient, user_id: uuid.UUID, title: str | None) -> dict[str, Any]:
    row: dict[str, Any] = {"user_id": str(user_id)}
    if title:
        row["title"] = title
    response = await client.table("chat_threads").insert(row).execute()
    return response.data[0]


async def delete_thread(client: AsyncClient, thread_id: uuid.UUID) -> None:
    await client.table("chat_threads").delete().eq("id", str(thread_id)).execute()


async def list_messages(client: AsyncClient, thread_id: uuid.UUID) -> list[UIMessage]:
    response = await (
        client.table("chat_messages")
        .select("id,role,content,parts")
        .eq("thread_id", str(thread_id))
        .order("sequence")
        .execute()
    )
    return [row_to_ui_message(row) for row in response.data]


async def _next_sequence(client: AsyncClient, thread_id: uuid.UUID) -> int:
    response = await (
        client.table("chat_messages")
        .select("sequence")
        .eq("thread_id", str(thread_id))
        .order("sequence", desc=True)
        .limit(1)
        .execute()
    )
    return response.data[0]["sequence"] + 1 if response.data else 0


def _message_row(message: UIMessage, message_id: str, thread_id: uuid.UUID, sequence: int) -> dict[str, Any]:
    return {
        "id": message_id,
        "thread_id": str(thread_id),
        "role": message.role,
        "content": message_text(message),
        "parts": message.parts,
        "sequence": sequence,
    }


async def append_turn(
    client: AsyncClient,
    thread: dict[str, Any],
    user_message: UIMessage,
    assistant_message: UIMessage,
) -> None:
    thread_id = uuid.UUID(thread["id"])
    sequence = await _next_sequence(client, thread_id)
    # One insert statement, so the user/assistant pair is written atomically. The client's
    # user message id is not a UUID, so the row gets a fresh one.
    await (
        client.table("chat_messages")
        .insert(
            [
                _message_row(user_message, str(uuid.uuid4()), thread_id, sequence),
                _message_row(assistant_message, assistant_message.id, thread_id, sequence + 1),
            ]
        )
        .execute()
    )

    # SQLAlchemy's onupdate never fires for PostgREST writes, so updated_at is set here.
    updates: dict[str, Any] = {"updated_at": datetime.now(UTC).isoformat()}
    if thread["title"] == DEFAULT_THREAD_TITLE:
        updates["title"] = title_from_text(message_text(user_message))
    await client.table("chat_threads").update(updates).eq("id", str(thread_id)).execute()
