import json
import uuid
from types import SimpleNamespace

import anyio
import anyio.lowlevel
import httpx
from pydantic import SecretStr
from pydantic_ai.usage import RunUsage

from app.assistant import router
from app.assistant.outputs import Citation, GroundedAnswer
from app.chat import orchestrator
from app.chat.messages import UIMessage
from app.config import settings
from app.database.chats import _citation_rows
from app.grounding import risk
from tests.assistant.test_tools import _passage

THREAD = {"id": str(uuid.uuid4()), "user_id": str(uuid.uuid4()), "title": "New chat"}
USER_MESSAGE = UIMessage(id="c1", role="user", parts=[{"type": "text", "text": "Apple revenue?"}])
SOURCE = _passage("Total net sales were $391.0 billion in 2024, up 2% from 2023.", ticker="AAPL")


def grounded(excerpt: str = "Total net sales were $391.0 billion") -> GroundedAnswer:
    return GroundedAnswer(
        answer="Apple's net sales were $391.0 billion [1].",
        citations=[Citation(citation_index=1, chunk_id=SOURCE.chunk_id, excerpt=excerpt)],
    )


def fake_agent(answer: GroundedAnswer, *, fail: bool = False, started: list | None = None):
    """Stands in for run_document_agent: reports a tool status, registers SOURCE, answers."""

    async def run(question, deps):
        if started is not None:
            started.append(question)
        deps.emit_status("searching", "Searching SEC filings…")
        await anyio.lowlevel.checkpoint()
        if fail:
            raise RuntimeError("model unavailable")
        deps.registry.register([SOURCE])
        return SimpleNamespace(output=answer, usage=RunUsage(requests=2, tool_calls=1), all_messages=list)

    return run


def use_fakes(monkeypatch, answer: GroundedAnswer | None = None, **agent_options) -> list:
    persisted: list = []

    async def fake_append_turn(_client, thread, user_message, assistant_message):
        # Yield to the event loop like a real network call; unshielded, this is where
        # a cancelled scope would abort the write.
        await anyio.lowlevel.checkpoint()
        persisted.append(assistant_message)

    monkeypatch.setattr(orchestrator.chats, "append_turn", fake_append_turn)
    monkeypatch.setattr(orchestrator, "run_document_agent", fake_agent(answer or grounded(), **agent_options))
    return persisted


async def _collect() -> list[dict | str]:
    chunks = []
    async for event in orchestrator.run_turn(None, THREAD, USER_MESSAGE):
        payload = event.removeprefix("data: ").strip()
        chunks.append(payload if payload == "[DONE]" else json.loads(payload))
    return chunks


def test_validated_answer_streams_statuses_text_and_citations_then_persists(monkeypatch):
    persisted = use_fakes(monkeypatch)

    chunks = anyio.run(_collect)

    types = [c if isinstance(c, str) else c["type"] for c in chunks]
    assert types[0] == "start" and types[-4:] == ["data-citation", "data-grounding-risk", "finish", "[DONE]"]
    risk = chunks[-3]
    assert risk["transient"] and risk["data"] == {"level": "none", "claims": []}
    statuses = [c for c in chunks if isinstance(c, dict) and c["type"] == "data-status"]
    assert [s["data"]["stage"] for s in statuses] == ["searching"]
    assert all(s["transient"] for s in statuses)
    assert types.index("data-status") < types.index("text-start")

    streamed = "".join(c["delta"] for c in chunks if isinstance(c, dict) and c["type"] == "text-delta")
    assert streamed == "Apple's net sales were $391.0 billion [1]."
    citation = chunks[-4]["data"]
    assert citation["chunkId"] == str(SOURCE.chunk_id) and citation["ticker"] == "AAPL"

    [assistant_message] = persisted
    assert assistant_message.id == chunks[0]["messageId"]
    assert assistant_message.parts[0]["text"] == streamed
    assert assistant_message.parts[1]["data"] == citation


def test_answer_that_fails_validation_is_neither_streamed_nor_persisted(monkeypatch):
    persisted = use_fakes(monkeypatch, grounded(excerpt="Net sales were a record"))

    chunks = anyio.run(_collect)

    types = [c if isinstance(c, str) else c["type"] for c in chunks]
    assert "text-delta" not in types and "data-citation" not in types
    assert chunks[-2] == {"type": "error", "errorText": orchestrator.GROUNDING_FAILURE_MESSAGE}
    assert chunks[-1] == "[DONE]"
    assert persisted == []


def test_agent_failure_becomes_a_generic_error_event(monkeypatch):
    persisted = use_fakes(monkeypatch, fail=True)

    chunks = anyio.run(_collect)

    assert chunks[-2] == {"type": "error", "errorText": orchestrator.AGENT_FAILURE_MESSAGE}
    assert "model unavailable" not in json.dumps(chunks[:-1])
    assert persisted == []


def test_answer_question_exposes_validation_and_usage(monkeypatch):
    use_fakes(monkeypatch, grounded(excerpt="Net sales were a record"))
    deps = orchestrator.DocumentAgentDeps(
        retriever=None, registry=orchestrator.TurnRegistry(), thread_id=uuid.uuid4(), user_id=uuid.uuid4()
    )

    outcome = anyio.run(orchestrator.answer_question, "Apple revenue?", deps)

    assert not outcome.validation.ok
    assert [issue.code for issue in outcome.validation.errors] == ["excerpt_not_in_chunk"]
    assert outcome.usage.requests == 2
    assert SOURCE.chunk_id in outcome.registry.passages_by_chunk_id


def test_turn_is_persisted_when_client_disconnects_mid_stream(monkeypatch):
    persisted = use_fakes(monkeypatch)

    async def consume_then_disconnect():
        with anyio.CancelScope() as scope:
            turn = orchestrator.run_turn(None, THREAD, USER_MESSAGE)
            try:
                while json.loads((await anext(turn)).removeprefix("data: "))["type"] != "text-start":
                    pass
                scope.cancel()
                await anext(turn)
            finally:
                await turn.aclose()

    anyio.run(consume_then_disconnect)

    [assistant_message] = persisted
    assert "$391.0 billion" in assistant_message.parts[0]["text"]


def test_citation_rows_mirror_the_streamed_citation_parts(monkeypatch):
    persisted = use_fakes(monkeypatch)
    anyio.run(_collect)

    [row] = _citation_rows(persisted[0])

    assert row["chunk_id"] == str(SOURCE.chunk_id)
    assert row["citation_index"] == 1
    assert row["filing_type"] == "10-K" and row["filing_date"] == SOURCE.filing_date.isoformat()
    assert row["message_id"] == persisted[0].id


def test_disconnect_while_the_agent_runs_cancels_the_agent(monkeypatch):
    cancelled = []

    async def slow_agent(question, deps):
        deps.emit_status("searching", "Searching SEC filings…")
        try:
            await anyio.sleep_forever()
        except BaseException:
            cancelled.append(True)
            raise

    persisted = use_fakes(monkeypatch)
    monkeypatch.setattr(orchestrator, "run_document_agent", slow_agent)

    async def disconnect_after_first_status():
        turn = orchestrator.run_turn(None, THREAD, USER_MESSAGE)
        await anext(turn)  # start
        await anext(turn)  # searching status
        await turn.aclose()
        await anyio.sleep(0.01)  # let the cancelled task run its handler
        # Checked inside the loop: at shutdown asyncio cancels leftover tasks by itself.
        assert cancelled == [True]

    anyio.run(disconnect_after_first_status)

    assert persisted == []


def _route_to(monkeypatch, *, advice=0.0, complexity="complex", fail=False):
    async def classify(question):
        if fail:
            raise httpx.ConnectError("jev down")
        return router.RouteDecision(
            scope="in_corpus",
            scope_confidence=0.95,
            advice_probability=advice,
            complexity=complexity,
            complexity_confidence=0.95,
            input_tokens=300,
            cost_usd=0.0,
            seconds=0.1,
        )

    async def offline_judge(claims, sources):
        raise httpx.ConnectError("no network in tests")

    monkeypatch.setattr(settings, "typesafe_api_key", SecretStr("test-key"))
    monkeypatch.setattr(router, "classify_question", classify)
    # The risk signal runs after the agent too; keep it offline.
    monkeypatch.setattr(risk, "judge_claims", offline_judge)


def _deps() -> orchestrator.DocumentAgentDeps:
    return orchestrator.DocumentAgentDeps(
        retriever=None, registry=orchestrator.TurnRegistry(), thread_id=uuid.uuid4(), user_id=uuid.uuid4()
    )


def test_confident_advice_question_gets_the_fixed_answer_without_running_the_agent(monkeypatch):
    started = []
    persisted = use_fakes(monkeypatch, started=started)
    _route_to(monkeypatch, advice=0.95)

    chunks = anyio.run(_collect)

    streamed = "".join(c["delta"] for c in chunks if isinstance(c, dict) and c["type"] == "text-delta")
    assert started == []
    assert streamed == router.SHORT_CIRCUIT_ANSWERS["refuse_advice"]
    assert not any(isinstance(c, dict) and c["type"] == "data-citation" for c in chunks)
    [assistant_message] = persisted
    assert assistant_message.parts[0]["text"] == streamed


def test_router_failure_falls_back_to_the_agent(monkeypatch):
    started = []
    use_fakes(monkeypatch, started=started)
    _route_to(monkeypatch, fail=True)

    outcome = anyio.run(orchestrator.answer_question, "Apple revenue?", _deps())

    assert started == ["Apple revenue?"]
    assert outcome.routing.route == "agent_large" and outcome.routing.error.startswith("ConnectError")
    assert outcome.validation.ok


def test_small_model_route_is_only_recorded_and_the_agent_still_runs(monkeypatch):
    started = []
    use_fakes(monkeypatch, started=started)
    _route_to(monkeypatch, complexity="simple")

    outcome = anyio.run(orchestrator.answer_question, "Apple revenue?", _deps())

    assert started == ["Apple revenue?"] and outcome.routing.route == "agent_small"
