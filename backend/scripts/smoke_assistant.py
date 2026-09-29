"""Run the client-brief questions through the real agent and the grounding validator.

Costs money: every question makes several calls to OPENAI_CHAT_MODEL. The run stops
before the next question once --budget (USD) is spent. One JSON line per question is
written to --out: tool calls, tokens, cost, latency and the validation result.

    cd backend && uv run python -m scripts.smoke_assistant --questions 1,10 --budget 1
"""

import argparse
import asyncio
import json
import time
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from openai import OpenAIError
from pydantic_ai.exceptions import AgentRunError
from pydantic_ai.messages import ModelResponse, ToolCallPart

from app.assistant.deps import DocumentAgentDeps, TurnRegistry
from app.assistant.progress import (
    add_progress_listener,
    elapsed_seconds,
    reset_progress_clock,
)
from app.chat.orchestrator import TurnOutcome, answer_question
from app.config import settings
from app.retrieval.retriever import DocumentRetriever

# gpt-5.5 list prices per 1M tokens (developers.openai.com/api/docs/pricing, 2026-09).
FALLBACK_INPUT_USD = Decimal(5)
FALLBACK_OUTPUT_USD = Decimal(30)
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "data" / "smoke"

# docs/client-brief.md, "Example analyst questions", verbatim.
QUESTIONS = [
    "Across Apple's 2021–2025 10-Ks, how did the revenue mix between iPhone, Services, Mac, iPad, and Wearables change, and which category appears to have contributed most to any mix shift?",
    "For Amazon, compare AWS operating income and margin against North America and International from 2021–2025. In which years did AWS appear to fund losses or weaker profitability elsewhere?",
    "How did NVIDIA describe demand drivers, customer concentration, and supply constraints for its Data Center business from fiscal 2021 through fiscal 2025?",
    "Across Microsoft's 2021–2025 filings, what changed in the way the company describes Azure, AI infrastructure, and cloud capacity constraints?",
    "For Alphabet, how did Google Search, YouTube ads, Google Network, subscriptions/platforms/devices, and Google Cloud revenue trends differ across the available 10-Ks?",
    "Which of the five companies added, removed, or materially changed risk-factor language related to AI, cloud infrastructure, export controls, supply chain concentration, or regulation between 2021 and 2025?",
    "For Apple and NVIDIA, what do the filings say about supplier concentration or dependence on third-party manufacturing, and did the wording become more or less urgent over time?",
    "Compare capital expenditures and purchase commitments for Microsoft, Alphabet, Amazon, and NVIDIA. What do the filings imply about the scale and timing of AI/cloud infrastructure investment?",
    "For each company, summarize the most important geographic revenue exposures disclosed in the latest 10-K, then identify any year-over-year changes that could matter to an analyst.",
    "If an analyst asks whether the filings prove that generative AI improved margins for any of these companies, what evidence exists in the corpus, and where should the bot refuse to infer beyond the filings?",
]


def _responses(outcome: TurnOutcome) -> list[ModelResponse]:
    return [message for message in outcome.messages if isinstance(message, ModelResponse)]


def _response_cost(response: ModelResponse) -> Decimal:
    try:
        return response.cost().total_price
    except LookupError:
        # Unknown model name: overestimate on purpose (no cache discount) so the budget holds.
        usage = response.usage
        return (usage.input_tokens * FALLBACK_INPUT_USD + usage.output_tokens * FALLBACK_OUTPUT_USD) / 1_000_000


def _cost(outcome: TurnOutcome) -> Decimal:
    # Priced per request: gpt-5.5 bills a request above 272K input tokens at a higher rate,
    # which pricing the summed usage would wrongly apply to the whole turn.
    return sum((_response_cost(response) for response in _responses(outcome)), Decimal(0))


def _record(number: int, question: str, outcome: TurnOutcome, wall_seconds: float, timeline: list) -> dict:
    responses = _responses(outcome)
    usage = outcome.usage
    return {
        "question_number": number,
        "question": question,
        "model": settings.openai_chat_model,
        "wall_seconds": round(wall_seconds, 1),
        "agent_seconds": round(outcome.agent_seconds, 1),
        "model_requests": usage.requests,
        "tool_calls": [
            {"tool": part.tool_name, "args": part.args_as_dict()}
            for response in responses
            for part in response.parts
            if isinstance(part, ToolCallPart) and part.tool_name in {"search_filings", "read_chunks", "read_chunk", "read_surrounding_chunks"}
        ],
        "tokens": {
            "input": usage.input_tokens,
            "cached_input": usage.cache_read_tokens,
            "output": usage.output_tokens,
            "reasoning": sum(response.usage.details.get("reasoning_tokens", 0) for response in responses),
            "largest_request_input": max((response.usage.input_tokens for response in responses), default=0),
        },
        "cost_usd": float(round(_cost(outcome), 4)),
        "validation": {
            "ok": outcome.validation.ok,
            "errors": [issue.model_dump() for issue in outcome.validation.errors],
            "warnings": [issue.model_dump() for issue in outcome.validation.warnings],
        },
        "insufficient_evidence": outcome.answer.insufficient_evidence,
        "citations": [
            {
                "index": citation.citation_index,
                "chunk_id": str(citation.chunk_id),
                "ticker": passage.ticker,
                "fiscal_year": passage.fiscal_year,
                "page": passage.page,
                "section": passage.section,
                "excerpt": citation.excerpt,
            }
            for citation in outcome.answer.citations
            if (passage := outcome.registry.passages_by_chunk_id.get(citation.chunk_id))
        ],
        "chunks_retrieved": len(outcome.registry.passages_by_chunk_id),
        "answer": outcome.answer.answer,
        "timeline": timeline,
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--questions", default="1-10", help='e.g. "1,3,10" or "1-10"')
    parser.add_argument("--budget", type=float, required=True, help="stop once this many USD are spent")
    parser.add_argument("--out", type=Path, default=OUTPUT_DIR / f"assistant-{datetime.now(UTC):%Y%m%d-%H%M%S}.jsonl")
    args = parser.parse_args()

    if "-" in args.questions:
        first, last = map(int, args.questions.split("-"))
        numbers = list(range(first, last + 1))
    else:
        numbers = [int(number) for number in args.questions.split(",")]

    timeline: list = []

    def log(message: str) -> None:
        timeline.append([round(elapsed_seconds(), 1), message])
        print(f"  [{elapsed_seconds():6.1f}s] {message}", flush=True)

    add_progress_listener(log)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    retriever = DocumentRetriever()
    spent = Decimal(0)

    with args.out.open("w") as out:
        for number in numbers:
            if spent >= Decimal(str(args.budget)):
                print(f"\nBudget of ${args.budget} reached (${spent:.2f} spent); stopping before question {number}.")
                break
            question = QUESTIONS[number - 1]
            print(f"\n### Q{number}: {question}", flush=True)
            timeline.clear()
            reset_progress_clock()
            deps = DocumentAgentDeps(
                retriever=retriever, registry=TurnRegistry(), thread_id=uuid.uuid4(), user_id=uuid.uuid4()
            )
            started = time.perf_counter()
            try:
                outcome = await answer_question(question, deps)
            except (AgentRunError, OpenAIError) as exc:
                # Usage of a failed run is lost, so the budget check cannot count it.
                print(f"  FAILED: {type(exc).__name__}: {exc}", flush=True)
                out.write(json.dumps({"question_number": number, "question": question, "error": repr(exc)}) + "\n")
                continue
            record = _record(number, question, outcome, time.perf_counter() - started, list(timeline))
            spent += _cost(outcome)
            out.write(json.dumps(record, default=str) + "\n")
            out.flush()

            validation = record["validation"]
            print(
                f"  => {record['wall_seconds']}s, {record['model_requests']} requests, "
                f"{len(record['tool_calls'])} tool calls, tokens in/cached/out "
                f"{record['tokens']['input']}/{record['tokens']['cached_input']}/{record['tokens']['output']}, "
                f"${record['cost_usd']:.3f} (total ${spent:.2f})"
            )
            print(
                f"  => validation ok={validation['ok']} errors={[e['code'] for e in validation['errors']]} "
                f"warnings={[w['code'] for w in validation['warnings']]} "
                f"insufficient={record['insufficient_evidence']} citations={len(record['citations'])}"
            )
    print(f"\nWrote {args.out} (${spent:.2f} spent)")


if __name__ == "__main__":
    asyncio.run(main())
