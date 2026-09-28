import json
import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api import chat as chat_api
from app.auth.dependencies import CurrentUser, get_current_user
from app.main import app

OWNER = CurrentUser(id=uuid.uuid4(), email="owner@example.com", access_token="owner-token")
OTHER = CurrentUser(id=uuid.uuid4(), email="other@example.com", access_token="other-token")
THREAD_ID = uuid.uuid4()
THREAD = {"id": str(THREAD_ID), "user_id": str(OWNER.id), "title": "New chat"}


def stream_body(role: str = "user", text: str = "What was Apple's revenue?") -> dict:
    return {
        "threadId": str(THREAD_ID),
        "messages": [{"id": "client-1", "role": role, "parts": [{"type": "text", "text": text}]}],
    }


@pytest.fixture
def client_as(monkeypatch):
    persisted: list[tuple] = []

    async def fake_get_thread(_service_client, thread_id):
        return THREAD if thread_id == THREAD_ID else None

    async def fake_list_messages(_client, _thread_id):
        return []

    async def fake_append_turn(_client, thread, user_message, assistant_message):
        persisted.append((thread, user_message, assistant_message))

    async def fake_delete_thread(_client, thread_id):
        persisted.append(("deleted", thread_id))

    monkeypatch.setattr(chat_api.chats, "get_thread", fake_get_thread)
    monkeypatch.setattr(chat_api.chats, "list_messages", fake_list_messages)
    monkeypatch.setattr(chat_api.chats, "delete_thread", fake_delete_thread)
    monkeypatch.setattr("app.chat.orchestrator.chats.append_turn", fake_append_turn)
    monkeypatch.setattr("app.chat.orchestrator.STUB_DELAY_SECONDS", 0)
    monkeypatch.setattr(app.state, "supabase", SimpleNamespace(), raising=False)

    def build(user: CurrentUser) -> TestClient:
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[chat_api.get_user_client] = lambda: SimpleNamespace()
        client = TestClient(app)
        client.persisted = persisted
        return client

    yield build
    app.dependency_overrides.clear()


def test_other_users_thread_history_is_forbidden(client_as):
    response = client_as(OTHER).get(f"/chat/threads/{THREAD_ID}/messages")
    assert response.status_code == 403


def test_other_user_cannot_stream_into_thread(client_as):
    client = client_as(OTHER)
    response = client.post("/chat/stream", json=stream_body())
    assert response.status_code == 403
    assert client.persisted == []


def test_unknown_thread_returns_404(client_as):
    response = client_as(OWNER).get(f"/chat/threads/{uuid.uuid4()}/messages")
    assert response.status_code == 404


@pytest.mark.parametrize(("role", "text"), [("assistant", "hi"), ("user", "   ")])
def test_stream_rejects_non_user_or_empty_last_message(client_as, role, text):
    response = client_as(OWNER).post("/chat/stream", json=stream_body(role, text))
    assert response.status_code == 422


def test_stream_emits_ai_sdk_protocol_and_persists_turn(client_as):
    client = client_as(OWNER)
    response = client.post("/chat/stream", json=stream_body())

    assert response.status_code == 200
    assert response.headers["x-vercel-ai-ui-message-stream"] == "v1"
    payloads = [line.removeprefix("data: ") for line in response.text.split("\n\n") if line]
    assert payloads[-1] == "[DONE]"
    chunks = [json.loads(p) for p in payloads[:-1]]
    types = [c["type"] for c in chunks]
    assert types[:2] == ["start", "text-start"] and types[-2:] == ["text-end", "finish"]

    streamed = "".join(c["delta"] for c in chunks if c["type"] == "text-delta")
    [(thread, user_message, assistant_message)] = client.persisted
    assert thread == THREAD
    assert user_message.parts[0]["text"] == "What was Apple's revenue?"
    assert assistant_message.parts[0]["text"] == streamed
    assert assistant_message.id == chunks[0]["messageId"]


def test_history_is_wrapped_in_messages_object(client_as):
    response = client_as(OWNER).get(f"/chat/threads/{THREAD_ID}/messages")
    assert response.status_code == 200
    assert response.json() == {"messages": []}


def test_owner_can_delete_thread(client_as):
    client = client_as(OWNER)
    response = client.delete(f"/chat/threads/{THREAD_ID}")
    assert response.status_code == 204
    assert client.persisted == [("deleted", THREAD_ID)]


def test_other_user_cannot_delete_thread(client_as):
    client = client_as(OTHER)
    response = client.delete(f"/chat/threads/{THREAD_ID}")
    assert response.status_code == 403
    assert client.persisted == []
