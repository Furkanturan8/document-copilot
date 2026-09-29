from app.retrieval.types import (
    MAX_AGENT_OUTPUT_CHARS,
    MAX_PASSAGE_EXCERPT_CHARS,
    format_passages_for_agent,
)
from tests.assistant.test_tools import _passage


def test_search_format_cuts_long_passages_to_an_excerpt():
    passage = _passage("x" * (MAX_PASSAGE_EXCERPT_CHARS + 100))

    output = format_passages_for_agent([passage])

    assert "x" * MAX_PASSAGE_EXCERPT_CHARS + "..." in output
    assert "x" * (MAX_PASSAGE_EXCERPT_CHARS + 1) not in output


def test_full_text_format_keeps_passages_whole_and_names_the_ones_left_out():
    passages = [_passage(f"{i}" * 3000) for i in range(5)]

    output = format_passages_for_agent(passages, full_text=True)

    shown = [p for p in passages if p.text in output]
    left_out = [p for p in passages if p.text not in output]
    assert len(shown) == 3 and len(left_out) == 2
    assert all(str(p.chunk_id) in output.splitlines()[-1] for p in left_out)
    assert len(output) <= MAX_AGENT_OUTPUT_CHARS + 200
