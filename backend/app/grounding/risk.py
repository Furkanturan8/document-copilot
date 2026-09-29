"""Semantic risk signal for a validated answer: numeric checks in code plus Jev's decisions.

Telemetry only. The deterministic validator decides whether an answer is shown; this never
fails an answer, it grades each claim none / warning / high for logs and the UI.
"""

import asyncio
from typing import Literal

import httpx
from pydantic import BaseModel

from app.assistant.deps import TurnRegistry
from app.assistant.outputs import GroundedAnswer
from app.config import settings
from app.grounding.claims import Claim, split_claims
from app.grounding.judge import JudgeUsage, SemanticDecision, judge_claims
from app.grounding.numeric import NumericCheck, check_claim_numbers

RiskLevel = Literal["none", "warning", "high"]
LEVEL_ORDER: dict[RiskLevel, int] = {"none": 0, "warning": 1, "high": 2}


class ClaimRisk(BaseModel):
    claim_id: str
    text: str
    citation_indices: list[int]
    level: RiskLevel
    reasons: list[str]
    decision: str | None  # Jev's decision, None when Jev did not run
    confidence: float | None
    numeric: NumericCheck


class RiskReport(BaseModel):
    level: RiskLevel
    claims: list[ClaimRisk]
    judge: JudgeUsage | None = None
    judge_error: str | None = None


def claim_level(decision: SemanticDecision | None, numeric: NumericCheck) -> tuple[RiskLevel, list[str]]:
    level: RiskLevel = "none"
    reasons: list[str] = []

    def raise_to(new: RiskLevel, reason: str) -> None:
        nonlocal level
        level = max(level, new, key=LEVEL_ORDER.__getitem__)
        reasons.append(reason)

    if numeric.unverified:
        raise_to("warning", f"figures not found in the cited sources: {', '.join(numeric.unverified)}")
    if decision is None or decision.confidence < settings.jev_warning_confidence:
        return level, reasons  # no judge, or too unsure to mean anything

    if decision.decision == "contradicted":
        high = decision.confidence >= settings.jev_high_confidence
        raise_to("high" if high else "warning", f"Jev: sources contradict the claim ({decision.confidence:.2f})")
    elif decision.decision == "uncertain":
        # Jev misreads restated units and computed shares; when code matched every figure,
        # its doubt is most likely that weakness, not missing evidence.
        if numeric.all_verified:
            reasons.append(f"Jev uncertain ({decision.confidence:.2f}), ignored: every figure matched in code")
        else:
            raise_to("warning", f"Jev: sources do not settle the claim ({decision.confidence:.2f})")
    return level, reasons


def _claim_sources(claims: list[Claim], answer: GroundedAnswer, registry: TurnRegistry) -> dict[str, dict[str, str]]:
    chunk_by_index = {citation.citation_index: citation.chunk_id for citation in answer.citations}
    return {
        claim.claim_id: {
            str(chunk_by_index[index]): registry.passages_by_chunk_id[chunk_by_index[index]].text
            for index in claim.citation_indices
            if index in chunk_by_index
        }
        for claim in claims
    }


async def assess_risk(answer: GroundedAnswer, registry: TurnRegistry) -> RiskReport:
    """For an answer that passed validation, so every cited chunk is in the registry."""
    claims = split_claims(answer.answer)
    sources = _claim_sources(claims, answer, registry)
    numeric = {claim.claim_id: check_claim_numbers(claim.text, list(sources[claim.claim_id].values())) for claim in claims}

    decisions: dict[str, SemanticDecision] = {}
    usage: JudgeUsage | None = None
    error: str | None = None
    if settings.typesafe_api_key is not None and claims:
        try:
            results, usage = await asyncio.wait_for(judge_claims(claims, sources), settings.jev_timeout_seconds)
            decisions = {decision.claim_id: decision for decision in results}
        # The signal is optional: a slow, down or changed judge API must not affect the answer.
        except (httpx.HTTPError, TimeoutError, KeyError, ValueError) as exc:
            error = f"{type(exc).__name__}: {exc}"

    claim_risks = []
    for claim in claims:
        decision = decisions.get(claim.claim_id)
        level, reasons = claim_level(decision, numeric[claim.claim_id])
        claim_risks.append(
            ClaimRisk(
                claim_id=claim.claim_id,
                text=claim.text,
                citation_indices=claim.citation_indices,
                level=level,
                reasons=reasons,
                decision=decision.decision if decision else None,
                confidence=decision.confidence if decision else None,
                numeric=numeric[claim.claim_id],
            )
        )
    overall = max((risk.level for risk in claim_risks), key=LEVEL_ORDER.__getitem__, default="none")
    return RiskReport(level=overall, claims=claim_risks, judge=usage, judge_error=error)
