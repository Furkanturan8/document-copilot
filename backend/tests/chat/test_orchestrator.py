import anyio
import anyio.lowlevel

from app.chat import orchestrator
from app.chat.messages import UIMessage

THREAD = {"id": "thread-1", "title": "New chat"}
USER_MESSAGE = UIMessage(id="c1", role="user", parts=[{"type": "text", "text": "Apple revenue?"}])


def test_turn_is_persisted_when_client_disconnects_mid_stream(monkeypatch):
    persisted = []

    async def fake_append_turn(_client, thread, user_message, assistant_message):
        # Yield to the event loop like a real network call; unshielded, this is where
        # a cancelled scope would abort the write.
        await anyio.lowlevel.checkpoint()
        persisted.append(assistant_message)

    monkeypatch.setattr(orchestrator.chats, "append_turn", fake_append_turn)
    monkeypatch.setattr(orchestrator, "STUB_DELAY_SECONDS", 0)

    async def consume_then_disconnect():
        with anyio.CancelScope() as scope:
            turn = orchestrator.run_turn(None, THREAD, USER_MESSAGE)
            try:
                await anext(turn)
                await anext(turn)
                scope.cancel()
                await anext(turn)
            finally:
                await turn.aclose()

    anyio.run(consume_then_disconnect)

    [assistant_message] = persisted
    assert "Apple revenue?" in assistant_message.parts[0]["text"]
