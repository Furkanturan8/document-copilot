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


def finish() -> str:
    return sse({"type": "finish", "finishReason": "stop"})


def error(error_text: str) -> str:
    return sse({"type": "error", "errorText": error_text})
