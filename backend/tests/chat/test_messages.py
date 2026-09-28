from app.chat.messages import (
    DEFAULT_THREAD_TITLE,
    TITLE_MAX_LENGTH,
    UIMessage,
    message_text,
    row_to_ui_message,
    title_from_text,
)


def test_message_text_joins_only_text_parts():
    message = UIMessage(
        id="1",
        role="user",
        parts=[{"type": "text", "text": "Hello "}, {"type": "step-start"}, {"type": "text", "text": "world"}],
    )
    assert message_text(message) == "Hello world"


def test_title_collapses_whitespace_and_truncates():
    assert title_from_text("  Apple   revenue\n2024 ") == "Apple revenue 2024"
    long_title = title_from_text("word " * 50)
    assert len(long_title) == TITLE_MAX_LENGTH
    assert long_title.endswith("…")


def test_blank_text_keeps_default_title():
    assert title_from_text("   ") == DEFAULT_THREAD_TITLE


def test_row_without_parts_falls_back_to_content():
    message = row_to_ui_message({"id": "abc", "role": "assistant", "content": "Stored text", "parts": None})
    assert message.parts == [{"type": "text", "text": "Stored text"}]
