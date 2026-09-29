"""Question routing with Jev before the agent runs: typed decisions in, a policy in code out.

Jev only classifies (scope, investment advice, complexity) with probabilities; `route`
turns that into an action. A confident out-of-scope or advice question is answered without
the agent; anything uncertain, and any routing failure, goes to the agent as before.
Measured with scripts/eval_router.py.
"""

import asyncio
import re
import time
from typing import Literal

import httpx
from pydantic import BaseModel

from app.config import settings
from app.grounding.judge import (
    EVALUATE_URL,
    JUDGE_MODEL,
    USD_PER_MILLION_INPUT_TOKENS,
    typesafe_headers,
)

Route = Literal["refuse_advice", "out_of_corpus", "agent_small", "agent_large"]
SHORT_CIRCUIT_ROUTES: set[Route] = {"refuse_advice", "out_of_corpus"}

CORPUS = (
    "Annual reports (form 10-K) of Apple (AAPL), Amazon (AMZN), Alphabet/Google (GOOGL), "
    "Microsoft (MSFT) and NVIDIA (NVDA) for fiscal years 2021 through 2025."
)
SCOPE_CRITERIA = {
    "in_corpus": "Asks about what the filings of Apple, Amazon, Alphabet, Microsoft or NVIDIA for fiscal 2021-2025 say",
    "other_company": "Asks about a company other than Apple, Amazon, Alphabet, Microsoft or NVIDIA",
    "other_period": "Asks about these companies only for years outside fiscal 2021-2025",
    "outside_filings": (
        "Asks for something annual reports cannot contain: current or future stock prices, "
        "forecasts, news, or events and statements outside the filings"
    ),
}
COMPLEXITY_CRITERIA = {
    "simple": "One company and one specific fact, figure or disclosure, for one or two years",
    "complex": "Several companies or years, a trend, comparison or change over time, or a synthesis of many disclosures",
}
ADVICE_CRITERIA = {
    "true": "Asks whether to buy, sell or hold a stock, which stock is the best investment, or for a price target",
    "false": "Asks what the filings say, even about risks, valuation inputs or shareholder returns",
}
# A question naming a corpus company is at least partly answerable ("Apple vs Samsung"),
# so Jev's other_company verdict alone must not turn it away.
CORPUS_COMPANY_RE = re.compile(
    r"\b(?:apple|aapl|amazon|amzn|aws|nvidia|nvda|microsoft|msft|alphabet|google|googl|goog)\b",
    re.IGNORECASE,
)
# Acting without the agent is only worth it when Jev is sure; everything else keeps today's path.
SHORT_CIRCUIT_CONFIDENCE = 0.8
SMALL_MODEL_CONFIDENCE = 0.8


# Fixed answers for questions the corpus cannot answer: no agent run, no citations.
SHORT_CIRCUIT_ANSWERS: dict[Route, str] = {
    "refuse_advice": (
        "I can't give investment advice, stock picks or price targets. I can tell you what the "
        "10-K filings of Apple, Amazon, Alphabet, Microsoft and NVIDIA for fiscal 2021-2025 say, "
        "for example about revenue, margins or risk factors."
    ),
    "out_of_corpus": (
        "That is outside what I can answer. My sources are the 10-K annual reports of Apple, Amazon, "
        "Alphabet, Microsoft and NVIDIA for fiscal 2021-2025; they contain no stock prices, forecasts, "
        "news, other years or other companies' filings."
    ),
}


class RouteDecision(BaseModel):
    scope: str
    scope_confidence: float
    advice_probability: float
    complexity: str
    complexity_confidence: float
    input_tokens: int
    cost_usd: float
    seconds: float


async def classify_question(question: str) -> RouteDecision:
    body = {
        "model": JUDGE_MODEL,
        "state": {"analyst_question": question, "corpus": CORPUS},
        "questions": {
            "scope": {
                "type": "choice",
                "instructions": "Can the corpus answer the analyst question, and if not, why?",
                "criteria": SCOPE_CRITERIA,
            },
            "advice": {
                "type": "noul",
                "instructions": "Does the analyst question ask for investment advice?",
                "criteria": ADVICE_CRITERIA,
            },
            "complexity": {
                "type": "choice",
                "instructions": "How much evidence does the analyst question need?",
                "criteria": COMPLEXITY_CRITERIA,
            },
        },
    }
    started = time.perf_counter()
    async with httpx.AsyncClient(headers=typesafe_headers(), timeout=10) as client:
        response = await client.post(EVALUATE_URL, json=body)
    response.raise_for_status()
    payload = response.json()
    answers = payload["answers"]
    input_tokens = payload["usage"]["input_tokens"]
    return RouteDecision(
        scope=answers["scope"]["choice"],
        scope_confidence=answers["scope"]["confidence"],
        advice_probability=answers["advice"]["noul"],
        complexity=answers["complexity"]["choice"],
        complexity_confidence=answers["complexity"]["confidence"],
        input_tokens=input_tokens,
        cost_usd=input_tokens * USD_PER_MILLION_INPUT_TOKENS / 1_000_000,
        seconds=time.perf_counter() - started,
    )


def route(decision: RouteDecision, question: str) -> Route:
    if decision.advice_probability >= SHORT_CIRCUIT_CONFIDENCE:
        return "refuse_advice"
    partly_in_corpus = decision.scope == "other_company" and CORPUS_COMPANY_RE.search(question)
    if (
        decision.scope != "in_corpus"
        and decision.scope_confidence >= SHORT_CIRCUIT_CONFIDENCE
        and not partly_in_corpus
    ):
        return "out_of_corpus"
    if decision.complexity == "simple" and decision.complexity_confidence >= SMALL_MODEL_CONFIDENCE:
        return "agent_small"
    return "agent_large"


class RoutingResult(BaseModel):
    route: Route
    decision: RouteDecision | None  # None when routing was skipped or failed
    error: str | None = None


async def decide_route(question: str) -> RoutingResult:
    """Never raises: without a key, or if Jev fails or is slow, the question goes to the agent."""
    if settings.typesafe_api_key is None:
        return RoutingResult(route="agent_large", decision=None)
    try:
        decision = await asyncio.wait_for(classify_question(question), settings.jev_router_timeout_seconds)
    except (httpx.HTTPError, TimeoutError, KeyError, ValueError) as exc:
        return RoutingResult(route="agent_large", decision=None, error=f"{type(exc).__name__}: {exc}")
    return RoutingResult(route=route(decision, question), decision=decision)
