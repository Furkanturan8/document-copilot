"""The PydanticAI document agent: instructions + retrieval tools -> GroundedAnswer."""

from functools import cache
from pathlib import Path

from pydantic_ai import Agent, UsageLimits
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.assistant.deps import DocumentAgentDeps
from app.assistant.outputs import GroundedAnswer
from app.assistant.status import emit_agent_done, emit_agent_start
from app.assistant.tools import (
    read_chunk,
    read_chunks,
    read_surrounding_chunks,
    search_filings,
)
from app.config import settings

INSTRUCTIONS = Path(__file__).with_name("instructions.md").read_text(encoding="utf-8")


@cache
def get_document_agent() -> Agent[DocumentAgentDeps, GroundedAnswer]:
    model = OpenAIChatModel(
        settings.openai_chat_model,
        provider=OpenAIProvider(api_key=settings.openai_api_key.get_secret_value()),
    )
    return Agent(
        model,
        deps_type=DocumentAgentDeps,
        output_type=GroundedAnswer,
        instructions=INSTRUCTIONS,
        tools=[search_filings, read_chunks, read_chunk, read_surrounding_chunks],
    )


async def run_document_agent(question: str, deps: DocumentAgentDeps) -> GroundedAnswer:
    emit_agent_start(deps, model=settings.openai_chat_model, request_limit=settings.openai_agent_request_limit)
    result = await get_document_agent().run(
        question,
        deps=deps,
        usage_limits=UsageLimits(request_limit=settings.openai_agent_request_limit),
    )
    usage = result.usage
    emit_agent_done(
        deps,
        requests=usage.requests,
        tool_calls=usage.tool_calls,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
    )
    return result.output
