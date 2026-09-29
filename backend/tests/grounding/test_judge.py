import json

import anyio
import httpx

from app.grounding import judge
from app.grounding.judge import CitedClaim, JudgeCase, cited_claim


def test_cited_part_is_the_clause_before_the_marker():
    answer = "U.S. revenue was $194.2 billion [3], and EMEA was $117.2 billion [4]. Margin fell sharply [5]."

    three, four = cited_claim(answer, 3), cited_claim(answer, 4)

    assert three.cited_part == "U.S. revenue was $194.2 billion"
    assert four.cited_part == "EMEA was $117.2 billion"
    assert three.sentence == four.sentence == "U.S. revenue was $194.2 billion, and EMEA was $117.2 billion."
    assert three.group == [3] and not three.shared


def test_short_table_cell_falls_back_to_its_row_and_shared_groups_are_flagged():
    answer = "| 2021 | 52.5% [1][6] | 18.7% [5][6] |"

    claim = cited_claim(answer, 5)

    assert claim.cited_part == claim.sentence == "2021 | 52.5% | 18.7% |"
    assert claim.group == [5, 6] and claim.shared
    assert cited_claim(answer, 9) is None


def test_judge_sends_claim_and_source_as_state_and_reads_the_choice():
    sent = []

    def gateway(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "answers": {
                    "relation": {
                        "type": "choice",
                        "choice": "contradicts",
                        "confidence": 0.9,
                        "probabilities": {"supports": 0.02, "contradicts": 0.95, "says_nothing": 0.03},
                    }
                },
                "usage": {"input_tokens": 1_000, "output_tokens": 20},
            },
        )

    async def judge_one():
        async with httpx.AsyncClient(transport=httpx.MockTransport(gateway)) as client:
            return await judge._judge_one(
                client,
                JudgeCase(
                    citation_index=3,
                    claim=CitedClaim(cited_part="Margin fell.", sentence="Margin fell.", group=[3]),
                    source_text="Margin rose to 75%.",
                ),
            )

    verdict = anyio.run(judge_one)

    assert verdict.citation_index == 3 and verdict.relation == "contradicts"
    assert verdict.probabilities["contradicts"] == 0.95
    assert verdict.confidence == 0.9
    assert verdict.input_tokens == 1_000 and verdict.cost_usd == 1_000 * 0.042 / 1_000_000
    [body] = sent
    assert body["model"] == judge.JUDGE_MODEL
    assert body["state"] == {
        "claim": "Margin fell.",
        "sentence_containing_the_claim": "Margin fell.",
        "source": "Margin rose to 75%.",
    }
    assert set(body["questions"]["relation"]["criteria"]) == {"supports", "contradicts", "says_nothing"}
