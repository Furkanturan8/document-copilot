import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from supabase import AsyncClient

from app.auth.dependencies import CurrentUser, CurrentUserDep
from app.chat import orchestrator
from app.chat.messages import UIMessage, message_text
from app.chat.streaming import UI_MESSAGE_STREAM_HEADERS
from app.database import chats
from app.database.supabase import create_user_client
from app.database.users import ensure_user

router = APIRouter(prefix="/chat", tags=["chat"])


class ThreadResponse(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")


class ThreadListResponse(BaseModel):
    threads: list[ThreadResponse]


class MessageHistoryResponse(BaseModel):
    messages: list[UIMessage]


class CreateThreadRequest(BaseModel):
    title: str | None = Field(default=None, max_length=255)


class ChatStreamRequest(BaseModel):
    """Body built by the frontend's chat transport: the thread plus the AI SDK UIMessages."""

    thread_id: uuid.UUID = Field(validation_alias="threadId")
    messages: list[UIMessage] = Field(min_length=1)


async def get_user_client(user: CurrentUserDep) -> AsyncClient:
    return await create_user_client(user.access_token)


UserClientDep = Annotated[AsyncClient, Depends(get_user_client)]


async def require_thread(request: Request, thread_id: uuid.UUID, user: CurrentUser) -> dict[str, Any]:
    thread = await chats.get_thread(request.app.state.supabase, thread_id)
    if thread is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Thread not found")
    if uuid.UUID(thread["user_id"]) != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have access to this thread")
    return thread


@router.get("/threads")
async def list_threads(user: CurrentUserDep, client: UserClientDep) -> ThreadListResponse:
    rows = await chats.list_threads(client, user.id)
    return ThreadListResponse(threads=[ThreadResponse.model_validate(row) for row in rows])


@router.post("/threads", status_code=status.HTTP_201_CREATED)
async def create_thread(
    request: Request, body: CreateThreadRequest, user: CurrentUserDep, client: UserClientDep
) -> ThreadResponse:
    # chat_threads.user_id references users.id, so the profile row must exist first.
    await ensure_user(request.app.state.supabase, user)
    row = await chats.create_thread(client, user.id, body.title)
    return ThreadResponse.model_validate(row)


@router.get("/threads/{thread_id}/messages")
async def list_messages(
    request: Request, thread_id: uuid.UUID, user: CurrentUserDep, client: UserClientDep
) -> MessageHistoryResponse:
    await require_thread(request, thread_id, user)
    return MessageHistoryResponse(messages=await chats.list_messages(client, thread_id))


@router.delete("/threads/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_thread(
    request: Request, thread_id: uuid.UUID, user: CurrentUserDep, client: UserClientDep
) -> None:
    await require_thread(request, thread_id, user)
    # Messages and citations go with it through ON DELETE CASCADE.
    await chats.delete_thread(client, thread_id)


@router.post("/stream")
async def stream_chat(
    request: Request, body: ChatStreamRequest, user: CurrentUserDep, client: UserClientDep
) -> StreamingResponse:
    thread = await require_thread(request, body.thread_id, user)

    # History comes from the database; only the newest message is taken from the request.
    user_message = body.messages[-1]
    if user_message.role != "user" or not message_text(user_message).strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "The last message must be a non-empty user message")

    return StreamingResponse(
        orchestrator.run_turn(client, thread, user_message),
        media_type="text/event-stream",
        headers=UI_MESSAGE_STREAM_HEADERS,
    )
