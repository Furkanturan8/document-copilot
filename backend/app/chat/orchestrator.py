"""One chat turn end to end: agent -> validate -> risk signal -> stream -> persist."""

import asyncio
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import anyio
import structlog
from pydantic_ai.messages import ModelMessage
from pydantic_ai.usage import RunUsage
from supabase import AsyncClient

from app.assistant.agent import run_document_agent
from app.assistant.deps import DocumentAgentDeps, TurnRegistry
from app.assistant.outputs import GroundedAnswer
from app.chat import streaming
from app.chat.messages import UIMessage, build_assistant_message, message_text
from app.database import chats
from app.grounding.risk import RiskReport, assess_risk
from app.grounding.validator import (
    ValidationResult,
    prune_unreferenced_citations,
    validate_grounded_answer,
)
from app.retrieval.retriever import DocumentRetriever

logger = structlog.get_logger()

AGENT_FAILURE_MESSAGE = "The assistant could not complete this answer. Please try again."
GROUNDING_FAILURE_MESSAGE = (
    "I found relevant source passages, but I could not verify the answer against them. "
    "Try a narrower question or split it into smaller parts."
)


@dataclass
class TurnOutcome:
    """Everything a turn produced, for the stream, the logs and smoke runs."""

    answer: GroundedAnswer
    validation: ValidationResult
    registry: TurnRegistry
    usage: RunUsage
    messages: list[ModelMessage]  # the full model/tool exchange, for smoke runs and debugging
    agent_seconds: float
    risk: RiskReport | None = None  # semantic risk signal; only for answers that passed validation


async def answer_question(question: str, deps: DocumentAgentDeps) -> TurnOutcome:
    started = time.perf_counter()
    result = await run_document_agent(question, deps)
    agent_seconds = time.perf_counter() - started

    # A citation the text never points to backs no claim; dropping it is not a repair.
    answer = prune_unreferenced_citations(result.output)
    validation = validate_grounded_answer(answer, deps.registry)
    logger.info(
        "grounding_validation",
        thread_id=str(deps.thread_id),
        ok=validation.ok,
        insufficient_evidence=answer.insufficient_evidence,
        citations=len(answer.citations),
        issues=[issue.model_dump() for issue in validation.issues],
    )
    outcome = TurnOutcome(answer, validation, deps.registry, result.usage, result.all_messages(), agent_seconds)
    if validation.ok and answer.citations:
        outcome.risk = await assess_risk(answer, deps.registry)
        logger.info(
            "grounding_risk",
            thread_id=str(deps.thread_id),
            level=outcome.risk.level,
            flagged=[claim.model_dump() for claim in outcome.risk.claims if claim.level != "none"],
            judge=outcome.risk.judge.model_dump() if outcome.risk.judge else None,
            judge_error=outcome.risk.judge_error,
        )
    return outcome


def _risk_payload(risk: RiskReport) -> dict[str, Any]:
    # Transient: a signal for the UI, not part of the stored answer.
    return {
        "level": risk.level,
        "claims": [
            {"citationIndices": claim.citation_indices, "level": claim.level, "reasons": claim.reasons}
            for claim in risk.claims
            if claim.level != "none"
        ],
    }


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
    yield streaming.start(assistant_id)

    # Tools report progress from the event loop thread, so a plain queue is enough;
    # None marks the end of the agent run.
    statuses: asyncio.Queue[tuple[str, str] | None] = asyncio.Queue()
    deps = DocumentAgentDeps(
        retriever=DocumentRetriever(),
        registry=TurnRegistry(),
        thread_id=uuid.UUID(thread["id"]),
        user_id=uuid.UUID(thread["user_id"]),
        on_status=lambda stage, message: statuses.put_nowait((stage, message)),
    )

    async def answer() -> TurnOutcome:
        try:
            return await answer_question(message_text(user_message), deps)
        finally:
            statuses.put_nowait(None)

    task = asyncio.create_task(answer())
    try:
        while (update := await statuses.get()) is not None:
            yield streaming.status(*update)
        outcome = await task
    except Exception:
        logger.exception("chat_turn_agent_failed", thread_id=thread["id"])
        yield streaming.error(AGENT_FAILURE_MESSAGE)
        yield streaming.DONE
        return
    finally:
        # A client that disconnects while the agent runs should not keep paying for it.
        task.cancel()

    if not outcome.validation.ok:
        # Fail closed: an unverified answer is neither shown nor stored.
        yield streaming.error(GROUNDING_FAILURE_MESSAGE)
        yield streaming.DONE
        return

    # The whole answer exists before streaming starts, so a disconnect mid-stream still
    # leaves a complete, validated answer to store for the next history load.
    assistant_message = build_assistant_message(assistant_id, outcome.answer, outcome.registry)
    text_id = str(uuid.uuid4())
    persisted = False
    try:
        yield streaming.text_start(text_id)
        for index, word in enumerate(outcome.answer.answer.split(" ")):
            yield streaming.text_delta(text_id, word if index == 0 else " " + word)
        yield streaming.text_end(text_id)
        for part in assistant_message.parts[1:]:
            yield streaming.data("citation", part["data"], part_id=part["id"])
        if outcome.risk is not None:
            yield streaming.data("grounding-risk", _risk_payload(outcome.risk), transient=True)
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
