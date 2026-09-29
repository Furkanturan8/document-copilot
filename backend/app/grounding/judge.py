"""Semantic citation check with Jev, TypeSafe AI's decision model.

The deterministic validator proves an excerpt is really in its chunk; this asks whether
the cited sources support what the answer says. Jev returns typed decisions with
probabilities, not prose. `judge_claims` is what the chat turn uses (as a risk signal, see
risk.py); `judge_citations` is the earlier per-citation variant, kept for the benchmark in
scripts/eval_judge.py.
"""

import asyncio
import re
import time

import httpx
from pydantic import BaseModel

from app.config import settings
from app.grounding.claims import SEGMENT_SPLIT_RE, Claim, clean_claim_text
from app.grounding.validator import marker_indices

EVALUATE_URL = "https://api.typesafe.ai/v1/systemone"
JUDGE_MODEL = "jev-latest"
USD_PER_MILLION_INPUT_TOKENS = 0.042  # output tokens are free (typesafe.ai, 2026-09)
# Option wording from TypeSafe's citation-check cookbook (docs.typesafe.ai/cookbooks/citation_check).
RELATION_CRITERIA = {
    "supports": "The source states the claim or directly implies that it is true",
    "contradicts": "The source states the opposite of the claim or implies it is false",
    "says_nothing": "The source does not address what the claim asserts, either way",
}
# The decision schema for claims: one typed choice plus Jev's confidence, no prose.
DECISION_CRITERIA = {
    "supported": "The sources state the claim or directly imply that it is true",
    "contradicted": "The sources state the opposite of the claim, or show part of it is false",
    "uncertain": "The sources do not settle the claim: they do not address it, or support only part of it",
}
MAX_STATE_CHARS = 60_000  # ~15K tokens per request, well inside Jev's 32K context
MARKER_GROUP_RE = re.compile(r"(?:\s*\[\d+(?:\s*,\s*\d+)*\])+")
MIN_CITED_PART_CHARS = 20  # shorter parts ("18.7%" in a table cell) need their whole row


class CitedClaim(BaseModel):
    cited_part: str  # the words right before the marker: what this one source should support
    sentence: str  # the whole sentence or table row, as context
    group: list[int]  # every citation in the marker group: [2][3] cites 2 and 3 together

    @property
    def shared(self) -> bool:
        return len(self.group) > 1


class JudgeCase(BaseModel):
    citation_index: int
    claim: CitedClaim
    source_text: str


class JudgeVerdict(BaseModel):
    citation_index: int
    relation: str
    confidence: float
    probabilities: dict[str, float]
    input_tokens: int
    cost_usd: float


class SemanticDecision(BaseModel):
    claim_id: str
    decision: str  # a DECISION_CRITERIA key
    confidence: float
    probabilities: dict[str, float]


class JudgeUsage(BaseModel):
    requests: int
    input_tokens: int
    cost_usd: float
    seconds: float


def cited_claim(answer_text: str, citation_index: int) -> CitedClaim | None:
    """The part of the answer that marker [n] vouches for, at its first occurrence.

    A sentence often cites several chunks, each for a different fact, so judging the whole
    sentence against one source would call most real citations unsupported.
    """
    for segment in SEGMENT_SPLIT_RE.split(answer_text):
        start = 0
        for group in MARKER_GROUP_RE.finditer(segment):
            part, start = segment[start : group.start()], group.end()
            indices = marker_indices(group.group())
            if citation_index in indices:
                sentence = clean_claim_text(segment)
                cited = clean_claim_text(part)
                return CitedClaim(
                    cited_part=cited if len(cited) >= MIN_CITED_PART_CHARS else sentence,
                    sentence=sentence,
                    group=sorted(indices),
                )
    return None


async def _judge_one(client: httpx.AsyncClient, case: JudgeCase) -> JudgeVerdict:
    response = await client.post(
        EVALUATE_URL,
        json={
            "model": JUDGE_MODEL,
            "state": {
                "claim": case.claim.cited_part,
                "sentence_containing_the_claim": case.claim.sentence,
                "source": case.source_text,
            },
            "questions": {
                "relation": {
                    "type": "choice",
                    "instructions": "How does the source relate to the claim?",
                    "criteria": RELATION_CRITERIA,
                }
            },
        },
    )
    response.raise_for_status()
    body = response.json()
    answer = body["answers"]["relation"]
    input_tokens = body["usage"]["input_tokens"]
    return JudgeVerdict(
        citation_index=case.citation_index,
        relation=answer["choice"],
        confidence=answer["confidence"],
        probabilities=answer["probabilities"],
        input_tokens=input_tokens,
        cost_usd=input_tokens * USD_PER_MILLION_INPUT_TOKENS / 1_000_000,
    )


async def judge_citations(cases: list[JudgeCase]) -> list[JudgeVerdict]:
    """One request per citation, run concurrently: each claim is judged against its own source only."""
    async with httpx.AsyncClient(headers=typesafe_headers(), timeout=30) as client:
        return list(await asyncio.gather(*(_judge_one(client, case) for case in cases)))


def typesafe_headers() -> dict[str, str]:
    if settings.typesafe_api_key is None:
        raise RuntimeError("TYPESAFE_API_KEY is not set")
    return {"Authorization": f"Bearer {settings.typesafe_api_key.get_secret_value()}"}


def _claim_state(claim: Claim, source_ids: list[str]) -> dict:
    state: dict = {"claim": claim.text, "sources": source_ids}
    if claim.context:
        state["table_header"] = claim.context
    return state


def _batched_bodies(claims: list[Claim], sources: dict[str, dict[str, str]]) -> list[dict]:
    """As few requests as fit the context: every claim is its own question, which Jev
    answers in parallel and in isolation against the shared state."""
    groups: list[list[Claim]] = [[]]
    size = 0
    for claim in claims:
        # Counts a shared source once per claim, so the estimate errs on the large side.
        claim_size = len(claim.text) + sum(len(text) for text in sources[claim.claim_id].values())
        if groups[-1] and size + claim_size > MAX_STATE_CHARS:
            groups.append([])
            size = 0
        groups[-1].append(claim)
        size += claim_size
    return [_batch_body(group, sources) for group in groups if group]


def _batch_body(claims: list[Claim], sources: dict[str, dict[str, str]]) -> dict:
    # Each source text goes in once, under a short id ("S1") the claims point to.
    source_ids: dict[str, str] = {}
    state_sources: dict[str, str] = {}
    state_claims: dict[str, dict] = {}
    for claim in claims:
        ids = []
        for key, text in sources[claim.claim_id].items():
            if key not in source_ids:
                source_ids[key] = f"S{len(source_ids) + 1}"
                state_sources[source_ids[key]] = text
            ids.append(source_ids[key])
        state_claims[claim.claim_id] = _claim_state(claim, ids)
    return {
        "model": JUDGE_MODEL,
        "state": {"sources": state_sources, "claims": state_claims},
        "questions": {
            claim.claim_id: {
                "type": "choice",
                "instructions": (
                    f"Judge only claims.{claim.claim_id}: how do the sources it lists relate to its claim? "
                    "Ignore every other claim."
                ),
                "criteria": DECISION_CRITERIA,
            }
            for claim in claims
        },
    }


def _isolated_bodies(claims: list[Claim], sources: dict[str, dict[str, str]]) -> list[dict]:
    """One request per claim with only its own sources: the baseline the batch is compared to."""
    bodies = []
    for claim in claims:
        texts = list(sources[claim.claim_id].values())
        state = _claim_state(claim, [f"S{n}" for n in range(1, len(texts) + 1)])
        state["sources"] = {f"S{n}": text for n, text in enumerate(texts, 1)}
        bodies.append(
            {
                "model": JUDGE_MODEL,
                "state": state,
                "questions": {
                    claim.claim_id: {
                        "type": "choice",
                        "instructions": "How do the sources relate to the claim?",
                        "criteria": DECISION_CRITERIA,
                    }
                },
            }
        )
    return bodies


async def _evaluate(client: httpx.AsyncClient, body: dict) -> tuple[list[SemanticDecision], int]:
    response = await client.post(EVALUATE_URL, json=body)
    response.raise_for_status()
    payload = response.json()
    decisions = [
        SemanticDecision(
            claim_id=claim_id,
            decision=answer["choice"],
            confidence=answer["confidence"],
            probabilities=answer["probabilities"],
        )
        for claim_id, answer in payload["answers"].items()
    ]
    return decisions, payload["usage"]["input_tokens"]


async def judge_claims(
    claims: list[Claim], sources: dict[str, dict[str, str]], *, batched: bool = True
) -> tuple[list[SemanticDecision], JudgeUsage]:
    """Decide each claim against all the sources it cites, together.

    `sources` maps claim_id -> {source key (e.g. chunk id): text}; a source cited by
    several claims is sent once per request.
    """
    bodies = _batched_bodies(claims, sources) if batched else _isolated_bodies(claims, sources)
    started = time.perf_counter()
    async with httpx.AsyncClient(headers=typesafe_headers(), timeout=30) as client:
        results = await asyncio.gather(*(_evaluate(client, body) for body in bodies))
    input_tokens = sum(tokens for _, tokens in results)
    usage = JudgeUsage(
        requests=len(bodies),
        input_tokens=input_tokens,
        cost_usd=input_tokens * USD_PER_MILLION_INPUT_TOKENS / 1_000_000,
        seconds=time.perf_counter() - started,
    )
    return [decision for decisions, _ in results for decision in decisions], usage
