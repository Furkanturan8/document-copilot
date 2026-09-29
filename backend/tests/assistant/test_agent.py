"""The agent wiring, driven by a scripted model instead of OpenAI."""

import uuid

import anyio
from pydantic_ai.messages import (
    ModelMessage,
    ModelResponse,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

from app.assistant import agent
from app.assistant.deps import DocumentAgentDeps, TurnRegistry
from app.retrieval.types import SearchFilters
from tests.assistant.test_tools import FakeRetriever, _passage


def test_agent_searches_then_returns_a_grounded_answer_citing_a_retrieved_chunk():
    hit = _passage("Data Center revenue was $47.5 billion.")
    retriever = FakeRetriever([hit])

    def scripted_model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        tool_returns = [
            part for message in messages for part in message.parts if isinstance(part, ToolReturnPart)
        ]
        if not tool_returns:
            return ModelResponse(
                parts=[ToolCallPart("search_filings", {"query": "data center revenue", "ticker": "NVDA"})]
            )
        output_tool = info.output_tools[0].name
        return ModelResponse(
            parts=[
                ToolCallPart(
                    output_tool,
                    {
                        "answer": "Data Center revenue was $47.5 billion [1].",
                        "citations": [
                            {"citation_index": 1, "chunk_id": str(hit.chunk_id), "excerpt": "$47.5 billion"}
                        ],
                    },
                )
            ]
        )

    deps = DocumentAgentDeps(
        retriever=retriever, registry=TurnRegistry(), thread_id=uuid.uuid4(), user_id=uuid.uuid4()
    )
    statuses = []
    deps.on_status = lambda stage, message: statuses.append(stage)

    with agent.get_document_agent().override(model=FunctionModel(scripted_model)):
        answer = anyio.run(agent.run_document_agent, "NVIDIA data center revenue?", deps).output

    assert retriever.calls == [("data center revenue", SearchFilters(ticker="NVDA"))]
    assert answer.citations[0].chunk_id == hit.chunk_id
    assert hit.chunk_id in deps.registry.passages_by_chunk_id
    assert statuses == ["analyzing", "searching", "verifying"]
