"""AI SDK UI message stream protocol (v1): server-sent events, one JSON chunk per event."""

import json
from typing import Any

UI_MESSAGE_STREAM_HEADERS = {
    "x-vercel-ai-ui-message-stream": "v1",
    "Cache-Control": "no-cache",
    # Stops reverse proxies (e.g. nginx on Railway) from buffering the stream.
    "X-Accel-Buffering": "no",
}

DONE = "data: [DONE]\n\n"


def sse(chunk: dict[str, Any]) -> str:
    return f"data: {json.dumps(chunk, separators=(',', ':'))}\n\n"


def start(message_id: str) -> str:
    return sse({"type": "start", "messageId": message_id})


def text_start(part_id: str) -> str:
    return sse({"type": "text-start", "id": part_id})


def text_delta(part_id: str, delta: str) -> str:
    return sse({"type": "text-delta", "id": part_id, "delta": delta})


def text_end(part_id: str) -> str:
    return sse({"type": "text-end", "id": part_id})


def data(name: str, payload: dict[str, Any], *, part_id: str | None = None, transient: bool = False) -> str:
    """A custom `data-<name>` part. Transient parts reach the client's onData callback but
    are not added to the message, so progress updates do not end up in the history."""
    chunk: dict[str, Any] = {"type": f"data-{name}", "data": payload}
    if part_id is not None:
        chunk["id"] = part_id
    if transient:
        chunk["transient"] = True
    return sse(chunk)


def status(stage: str, message: str) -> str:
    return data("status", {"stage": stage, "message": message}, transient=True)


def finish() -> str:
    return sse({"type": "finish", "finishReason": "stop"})


def error(error_text: str) -> str:
    return sse({"type": "error", "errorText": error_text})
