"""Measure the Jev question router on hand-labelled questions. No agent, no OpenAI calls.

The metric that matters most is the first line of the report: an in-corpus question must
never be short-circuited, since that answers a legitimate question with a refusal. Jev
costs $0.042 per 1M input tokens, so a run costs a fraction of a cent.

    cd backend && uv run python -m scripts.eval_router
"""

import asyncio
import json
import time
from datetime import UTC, datetime
from pathlib import Path

from app.assistant.router import classify_question, route
from scripts.smoke_assistant import QUESTIONS as CLIENT_BRIEF

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "data" / "smoke"

# (question, scope, asks_for_advice, complexity); complexity only matters in corpus.
LABELLED = [
    *[(question, "in_corpus", False, "complex") for question in CLIENT_BRIEF],
    ("What was Apple's total net sales in fiscal 2024?", "in_corpus", False, "simple"),
    ("How much did NVIDIA spend on research and development in fiscal 2025?", "in_corpus", False, "simple"),
    ("When does Microsoft's fiscal year end?", "in_corpus", False, "simple"),
    ("How many full-time employees did Amazon have at the end of 2023?", "in_corpus", False, "simple"),
    ("What was Alphabet's operating income in 2022?", "in_corpus", False, "simple"),
    ("Which foundries manufacture NVIDIA's chips according to its latest 10-K?", "in_corpus", False, "simple"),
    ("What was AWS net sales in 2025?", "in_corpus", False, "simple"),
    ("Did Microsoft pay a dividend in fiscal 2025, and how much per share?", "in_corpus", False, "simple"),
    ("What risks does Apple list that could affect its stock price?", "in_corpus", False, "simple"),
    ("How did Amazon's share repurchase activity change between 2021 and 2025?", "in_corpus", False, "complex"),
    ("What does NVIDIA say about the valuation of its inventory in fiscal 2024?", "in_corpus", False, "simple"),
    ("What was Tesla's revenue in 2024?", "other_company", False, None),
    ("How did Meta describe its AI capital expenditures in its 2025 10-K?", "other_company", False, None),
    ("Compare Netflix and Disney streaming subscriber growth.", "other_company", False, None),
    ("What was Apple's revenue in fiscal 2015?", "other_period", False, None),
    ("How did Microsoft describe cloud computing in its 2012 annual report?", "other_period", False, None),
    ("What is NVIDIA's stock price today?", "outside_filings", False, None),
    ("Will Microsoft beat analyst earnings estimates next quarter?", "outside_filings", False, None),
    ("What did Jensen Huang announce at the GTC 2025 keynote?", "outside_filings", False, None),
    ("What will Amazon's revenue be in 2027?", "outside_filings", False, None),
    ("Should I buy NVIDIA stock now?", "outside_filings", True, None),
    ("Which of these five companies is the best investment for 2026?", "outside_filings", True, None),
    ("Is Apple overvalued? Give me a price target.", "outside_filings", True, None),
    ("Based on the 10-Ks, should I sell my Amazon shares?", "in_corpus", True, None),
]


def expected_route(scope: str, advice: bool, complexity: str | None) -> str:
    if advice:
        return "refuse_advice"
    if scope != "in_corpus":
        return "out_of_corpus"
    return "agent_small" if complexity == "simple" else "agent_large"


async def main() -> None:
    started = time.perf_counter()
    decisions = await asyncio.gather(*(classify_question(question) for question, *_ in LABELLED))
    wall = time.perf_counter() - started

    rows = []
    for (question, scope, advice, complexity), decision in zip(LABELLED, decisions, strict=True):
        rows.append(
            {
                "question": question,
                "expected": expected_route(scope, advice, complexity),
                "routed": route(decision),
                "label": {"scope": scope, "advice": advice, "complexity": complexity},
                "decision": decision.model_dump(),
            }
        )

    in_corpus = [r for r in rows if r["label"]["scope"] == "in_corpus" and not r["label"]["advice"]]
    short_circuited = [r for r in in_corpus if r["routed"] in ("refuse_advice", "out_of_corpus")]
    should_short = [r for r in rows if r["expected"] in ("refuse_advice", "out_of_corpus")]
    caught = [r for r in should_short if r["routed"] == r["expected"]]
    sized = [r for r in in_corpus if r["routed"] in ("agent_small", "agent_large")]
    print(f"in-corpus questions wrongly short-circuited: {len(short_circuited)}/{len(in_corpus)}  (must be 0)")
    print(f"out-of-scope / advice questions short-circuited correctly: {len(caught)}/{len(should_short)}")
    print(f"in-corpus model size as labelled: {sum(r['routed'] == r['expected'] for r in sized)}/{len(sized)}")
    print(f"exact route overall: {sum(r['routed'] == r['expected'] for r in rows)}/{len(rows)}")

    print("\nMismatches:")
    for r in rows:
        if r["routed"] != r["expected"]:
            d = r["decision"]
            print(
                f"  expected {r['expected']:13} got {r['routed']:13} | scope {d['scope']} {d['scope_confidence']:.2f}, "
                f"advice {d['advice_probability']:.2f}, {d['complexity']} {d['complexity_confidence']:.2f} | {r['question'][:70]}"
            )

    latencies = sorted(d.seconds for d in decisions)
    print(
        f"\n{len(rows)} questions, {wall:.1f}s wall; per-question latency median {latencies[len(latencies) // 2]:.2f}s "
        f"max {latencies[-1]:.2f}s; input tokens {sum(d.input_tokens for d in decisions)}, "
        f"cost ${sum(d.cost_usd for d in decisions):.5f}"
    )
    out = OUTPUT_DIR / f"router-{datetime.now(UTC):%Y%m%d-%H%M%S}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(r) + "\n" for r in rows))
    print(f"Wrote {out}")


if __name__ == "__main__":
    asyncio.run(main())
