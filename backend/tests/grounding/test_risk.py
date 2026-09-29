import json

import anyio
import httpx

from app.assistant.deps import TurnRegistry
from app.assistant.outputs import Citation, GroundedAnswer
from app.config import settings
from app.grounding import judge, risk
from app.grounding.claims import Claim, split_claims
from app.grounding.judge import SemanticDecision
from app.grounding.numeric import check_claim_numbers
from app.grounding.risk import assess_risk, claim_level
from app.grounding.validator import validate_grounded_answer
from tests.assistant.test_tools import _passage

SEGMENTS = [
    "| Net sales | $387,497 | $426,305 |",
    "| Operating income | $24,967 | $29,619 |",
]


# --- Claims ---------------------------------------------------------------------------


def test_claims_are_cited_sentences_and_rows_with_every_citation_and_the_table_header():
    answer = (
        "AWS led [1]. U.S. revenue was $194.2 billion [3], and EMEA $117.2 billion [4].\n\n"
        "| Year | North America | AWS |\n|---|---:|---:|\n"
        "| 2021 | $7.3B [2][3] | $18.5B [6][7] |\n"
        "| 2021 | $7.3B [2][3] | $18.5B [6][7] |"
    )

    claims = split_claims(answer)

    assert [c.text for c in claims] == [
        "AWS led.",
        "U.S. revenue was $194.2 billion, and EMEA $117.2 billion.",
        "2021 | $7.3B | $18.5B |",
    ]
    assert claims[1].citation_indices == [3, 4]
    assert claims[2].citation_indices == [2, 3, 6, 7]
    assert claims[2].context == "Year | North America | AWS |"


# --- Numeric validator ----------------------------------------------------------------


def _statuses(claim: str, sources=SEGMENTS) -> dict[str, str]:
    return {check.figure: check.status for check in check_claim_numbers(claim, sources).figures}


def test_numbers_match_exactly_after_unit_conversion_or_as_computed_percentages():
    statuses = _statuses("2024 | $24,967 | $25.0B / 6.4% | up 11.4% |")

    assert statuses == {"$24,967": "exact", "$25.0B": "scaled", "6.4%": "derived", "11.4%": "unverified"}


def test_growth_rate_is_derived_from_two_cited_numbers():
    assert _statuses("Net sales grew 10.0%")["10.0%"] == "derived"  # 426,305 / 387,497 - 1


def test_the_rest_of_a_stated_share_is_derived():
    assert _statuses("48% U.S. / 52% non-U.S.", ["| United States | 48% |"]) == {"48%": "exact", "52%": "derived"}


def test_changed_figures_are_unverified():
    assert _statuses("$27.0B / 7.4%") == {"$27.0B": "unverified", "7.4%": "unverified"}


def test_integer_percentages_are_not_derived_because_random_pairs_match_them():
    assert _statuses("margin was 6%") == {"6%": "unverified"}


def test_years_counts_and_form_names_are_not_figures():
    assert check_claim_numbers("The 10-K for fiscal 2024 lists 3 segments", SEGMENTS).figures == []


# --- Risk levels ----------------------------------------------------------------------


def _decision(kind: str, confidence: float) -> SemanticDecision:
    return SemanticDecision(claim_id="c1", decision=kind, confidence=confidence, probabilities={kind: confidence})


VERIFIED = check_claim_numbers("$25.0B", SEGMENTS)
UNCHECKED = check_claim_numbers("Margins improved", SEGMENTS)


def test_confident_contradiction_is_high_risk():
    assert claim_level(_decision("contradicted", 0.9), VERIFIED)[0] == "high"


def test_medium_confidence_is_a_warning_and_low_confidence_is_ignored():
    assert claim_level(_decision("contradicted", 0.6), UNCHECKED)[0] == "warning"
    assert claim_level(_decision("uncertain", 0.6), UNCHECKED)[0] == "warning"
    assert claim_level(_decision("contradicted", 0.3), UNCHECKED) == ("none", [])


def test_jev_doubt_is_ignored_when_code_verified_every_figure():
    level, reasons = claim_level(_decision("uncertain", 0.95), VERIFIED)

    assert level == "none" and "ignored" in reasons[0]


def test_unverified_figures_warn_even_when_jev_agrees():
    level, reasons = claim_level(_decision("supported", 0.99), check_claim_numbers("$27.0B", SEGMENTS))

    assert level == "warning" and "$27.0B" in reasons[0]


# --- Batched Jev requests ---------------------------------------------------------------


def test_one_request_carries_every_claim_as_its_own_question_with_each_source_once():
    claims = [
        Claim(claim_id="c1", text="Net sales were $387.5B.", citation_indices=[1]),
        Claim(claim_id="c2", text="Operating income was $25.0B.", citation_indices=[1, 2]),
    ]
    sources = {"c1": {"chunk-a": "sales table"}, "c2": {"chunk-a": "sales table", "chunk-b": "income table"}}

    [body] = judge._batched_bodies(claims, sources)

    assert body["state"]["sources"] == {"S1": "sales table", "S2": "income table"}
    assert body["state"]["claims"]["c2"] == {"claim": "Operating income was $25.0B.", "sources": ["S1", "S2"]}
    assert set(body["questions"]) == {"c1", "c2"}
    assert set(body["questions"]["c1"]["criteria"]) == {"supported", "contradicted", "uncertain"}


def test_claims_beyond_the_context_budget_go_to_a_second_request(monkeypatch):
    monkeypatch.setattr(judge, "MAX_STATE_CHARS", 100)
    claims = [Claim(claim_id=f"c{n}", text="x" * 30, citation_indices=[n]) for n in (1, 2, 3)]
    sources = {f"c{n}": {f"chunk-{n}": "y" * 40} for n in (1, 2, 3)}

    bodies = judge._batched_bodies(claims, sources)

    assert [list(body["questions"]) for body in bodies] == [["c1"], ["c2"], ["c3"]]


# --- End to end, offline --------------------------------------------------------------


def _answer_and_registry():
    table = _passage("| Operating income | $24,967 | $29,619 |")
    answer = GroundedAnswer(
        answer="Operating income reached $25.0B [1].",
        citations=[Citation(citation_index=1, chunk_id=table.chunk_id, excerpt="Operating income | $24,967")],
    )
    registry = TurnRegistry()
    registry.register([table])
    return answer, registry


def test_jev_contradiction_raises_the_signal_but_never_fails_the_answer(monkeypatch):
    answer, registry = _answer_and_registry()
    sent = []

    def jev(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        sent.append(body)
        return httpx.Response(
            200,
            json={
                "answers": {
                    "c1": {"choice": "contradicted", "confidence": 0.93, "probabilities": {"contradicted": 0.93}}
                },
                "usage": {"input_tokens": 400, "output_tokens": 10},
            },
        )

    real_client = httpx.AsyncClient
    monkeypatch.setattr(settings, "typesafe_api_key", "test-key")
    monkeypatch.setattr(judge, "_headers", dict)
    monkeypatch.setattr(
        judge.httpx, "AsyncClient", lambda **kwargs: real_client(transport=httpx.MockTransport(jev), **kwargs)
    )

    report = anyio.run(assess_risk, answer, registry)

    assert validate_grounded_answer(answer, registry).ok
    assert report.level == "high" and report.claims[0].decision == "contradicted"
    assert report.judge.requests == 1 and len(sent) == 1


def test_a_failing_judge_is_recorded_and_numeric_checks_still_run(monkeypatch):
    answer, registry = _answer_and_registry()

    async def broken_judge(claims, sources):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(settings, "typesafe_api_key", "test-key")
    monkeypatch.setattr(risk, "judge_claims", broken_judge)

    report = anyio.run(assess_risk, answer, registry)

    assert report.judge_error.startswith("ConnectError")
    assert report.level == "none" and report.claims[0].numeric.all_verified


def test_without_a_key_jev_is_not_called():
    answer, registry = _answer_and_registry()

    report = anyio.run(assess_risk, answer, registry)

    assert report.judge is None and report.judge_error is None
    assert report.claims[0].decision is None
