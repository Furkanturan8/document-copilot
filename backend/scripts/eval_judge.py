"""Measure the semantic risk signal (numeric checks + Jev) on real answers.

Positives come from answers that passed the deterministic validator in a smoke run; they
are assumed supported, not hand-labelled. Negatives are built from them so the right
verdict is known: a changed number, a flipped direction word, or unrelated sources.

--unit claim (default) scores what the chat turn runs: each cited sentence or table row
against all its sources, through app/grounding/risk.py's levels; --mode compares one
batched request per answer with one request per claim. --unit citation is the earlier
per-citation benchmark, kept for comparison. Jev costs $0.042 per 1M input tokens.

    cd backend && uv run python -m scripts.eval_judge ../data/smoke/assistant-<run>.jsonl
    cd backend && uv run python -m scripts.eval_judge <run>.jsonl --mode isolated
    cd backend && uv run python -m scripts.eval_judge <run>.jsonl --unit citation
"""

import argparse
import asyncio
import json
import random
import re
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from app.database.documents import get_chunks_by_ids
from app.database.session import get_session
from app.grounding.claims import Claim, split_claims
from app.grounding.judge import (
    CitedClaim,
    JudgeCase,
    cited_claim,
    judge_citations,
    judge_claims,
)
from app.grounding.numeric import check_claim_numbers
from app.grounding.risk import claim_level

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "data" / "smoke"
BATCH_SIZE = 10  # concurrent requests; TypeSafe's rate limits are not published
YEAR_RE = re.compile(r"^(?:19|20)\d{2}$")
NUMBER_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")
DIRECTION_SWAPS = {
    "increased": "decreased",
    "decreased": "increased",
    "increase": "decrease",
    "decrease": "increase",
    "rose": "fell",
    "fell": "rose",
    "grew": "declined",
    "declined": "grew",
    "higher": "lower",
    "lower": "higher",
}
DIRECTION_RE = re.compile(r"\b(" + "|".join(DIRECTION_SWAPS) + r")\b")


def _change_number(claim: str) -> str | None:
    for match in NUMBER_RE.finditer(claim):
        raw = match.group()
        if YEAR_RE.match(raw):
            continue
        value = float(raw.replace(",", "")) * 1.37
        decimals = len(raw.split(".")[1]) if "." in raw else 0
        changed = f"{value:,.{decimals}f}" if "," in raw else f"{value:.{decimals}f}"
        return claim[: match.start()] + changed + claim[match.end() :]
    return None


def _flip_direction(claim: str) -> str | None:
    if not DIRECTION_RE.search(claim):
        return None
    return DIRECTION_RE.sub(lambda match: DIRECTION_SWAPS[match.group()], claim, count=1)


def load_positives(paths: list[Path]) -> list[dict]:
    records = [json.loads(line) for path in paths for line in path.open()]
    passing = [r for r in records if r.get("validation", {}).get("ok") and not r.get("insufficient_evidence")]
    citations = [(r, c) for r in passing for c in r["citations"] if "chunk_id" in c]
    with get_session() as session:
        chunks = get_chunks_by_ids(session, [uuid.UUID(c["chunk_id"]) for r in passing for c in r["citations"]])
    positives = []
    for record, citation in citations:
        claim = cited_claim(record["answer"], citation["index"])
        if claim is None:
            continue
        chunk_by_index = {c["index"]: c["chunk_id"] for c in record["citations"]}
        positives.append(
            {
                "question_number": record["question_number"],
                "citation_index": citation["index"],
                "ticker": citation["ticker"],
                "claim": claim.model_dump(),
                "source": _group_source(claim.group, chunk_by_index, chunks),
            }
        )
    return positives


def _group_source(group: list[int], chunk_by_index: dict, chunks: dict) -> str:
    """Sources cited together are shown together: [2][3] vouches for the claim as a pair."""
    texts = [chunks[uuid.UUID(chunk_by_index[index])][0].content for index in group if index in chunk_by_index]
    if len(texts) == 1:
        return texts[0]
    return "\n\n".join(f"Source {n}:\n{text}" for n, text in enumerate(texts, 1))


def _mutated(claim: dict, mutate) -> dict | None:
    # The mutation applies to the cited part and, for context, to the same words in the sentence.
    changed = mutate(claim["cited_part"])
    if changed is None:
        return None
    return {**claim, "cited_part": changed, "sentence": claim["sentence"].replace(claim["cited_part"], changed)}


def build_cases(positives: list[dict], seed: int) -> list[dict]:
    rng = random.Random(seed)
    cases = [{**p, "kind": "real", "expected": "supports"} for p in positives]
    for position, positive in enumerate(positives):
        if changed := _mutated(positive["claim"], _change_number):
            cases.append({**positive, "kind": "changed_number", "claim": changed, "expected": "not_supports"})
        if flipped := _mutated(positive["claim"], _flip_direction):
            cases.append({**positive, "kind": "flipped_direction", "claim": flipped, "expected": "not_supports"})
        others = [p for p in positives if p["ticker"] != positive["ticker"]] or [
            p for i, p in enumerate(positives) if i != position
        ]
        unrelated = rng.choice(others)
        cases.append({**positive, "kind": "unrelated_source", "source": unrelated["source"], "expected": "not_supports"})
    return cases


async def run(cases: list[dict]) -> list[dict]:
    results = []
    for start in range(0, len(cases), BATCH_SIZE):
        batch = cases[start : start + BATCH_SIZE]
        verdicts = await judge_citations(
            [
                JudgeCase(
                    citation_index=i,
                    claim=CitedClaim(**c["claim"]),
                    source_text=c["source"],
                )
                for i, c in enumerate(batch)
            ]
        )
        results += [{**case, "verdict": v.model_dump()} for case, v in zip(batch, verdicts, strict=True)]
        print(f"  judged {len(results)}/{len(cases)}", flush=True)
    return results


def _report(results: list[dict], seconds: float) -> None:
    def accepted(result: dict, threshold: float) -> bool:
        return result["verdict"]["probabilities"].get("supports", 0) >= threshold

    print(f"\n{len(results)} cases in {seconds:.1f}s")
    for threshold in (0.5, 0.8):
        print(f"\nAccept when P(supports) >= {threshold}:")
        groups = [
            ("real, one source cited", lambda r: r["kind"] == "real" and len(r["claim"]["group"]) == 1),
            ("real, sources cited together", lambda r: r["kind"] == "real" and len(r["claim"]["group"]) > 1),
            ("changed_number", lambda r: r["kind"] == "changed_number"),
            ("flipped_direction", lambda r: r["kind"] == "flipped_direction"),
            ("unrelated_source", lambda r: r["kind"] == "unrelated_source"),
        ]
        for name, belongs in groups:
            group = [r for r in results if belongs(r)]
            if not group:
                continue
            correct = sum(accepted(r, threshold) == (r["expected"] == "supports") for r in group)
            print(f"  {name:28} {correct}/{len(group)} correct ({100 * correct / len(group):.0f}%)")
        answers: dict[int, bool] = {}
        for r in results:
            if r["kind"] == "real":
                answers[r["question_number"]] = answers.get(r["question_number"], True) and accepted(r, threshold)
        print(f"  answers with every sampled citation accepted: {sum(answers.values())}/{len(answers)}")
    tokens = sum(r["verdict"]["input_tokens"] for r in results)
    cost = sum(r["verdict"]["cost_usd"] for r in results)
    print(f"\ninput tokens {tokens}, cost ${cost:.5f}")


def load_claim_positives(paths: list[Path]) -> list[dict]:
    records = [json.loads(line) for path in paths for line in path.open()]
    passing = [r for r in records if r.get("validation", {}).get("ok") and not r.get("insufficient_evidence")]
    with get_session() as session:
        chunks = get_chunks_by_ids(session, [uuid.UUID(c["chunk_id"]) for r in passing for c in r["citations"]])
    positives = []
    for record in passing:
        cited = {c["index"]: c for c in record["citations"]}
        for claim in split_claims(record["answer"]):
            indices = [i for i in claim.citation_indices if i in cited]
            positives.append(
                {
                    "question_number": record["question_number"],
                    "tickers": sorted({cited[i]["ticker"] for i in indices}),
                    "claim": claim.model_dump(),
                    "sources": {
                        cited[i]["chunk_id"]: chunks[uuid.UUID(cited[i]["chunk_id"])][0].content for i in indices
                    },
                }
            )
    return positives


def build_claim_cases(positives: list[dict], seed: int) -> list[dict]:
    rng = random.Random(seed)
    cases = [{**p, "kind": "real"} for p in positives]
    for positive in positives:
        for kind, mutate in (("changed_number", _change_number), ("flipped_direction", _flip_direction)):
            if changed := mutate(positive["claim"]["text"]):
                cases.append({**positive, "kind": kind, "claim": {**positive["claim"], "text": changed}})
        others = [p for p in positives if p["question_number"] != positive["question_number"]]
        cases.append({**positive, "kind": "unrelated_source", "sources": rng.choice(others)["sources"]})
    for n, case in enumerate(cases, 1):
        case["claim"] = {**case["claim"], "claim_id": f"k{n}"}  # unique across every request
    return cases


async def run_claims(cases: list[dict], *, batched: bool) -> tuple[list[dict], list]:
    """Batched: one request per (answer, case kind), like one chat turn. Isolated: one per claim."""
    groups: dict[tuple, list[dict]] = {}
    for case in cases:
        key = (case["question_number"], case["kind"]) if batched else (case["claim"]["claim_id"],)
        groups.setdefault(key, []).append(case)

    async def judge_group(group: list[dict]):
        claims = [Claim(**case["claim"]) for case in group]
        return await judge_claims(claims, {c["claim"]["claim_id"]: c["sources"] for c in group}, batched=batched)

    outcomes = await asyncio.gather(*(judge_group(group) for group in groups.values()))
    decisions = {d.claim_id: d for group_decisions, _ in outcomes for d in group_decisions}
    results = []
    for case in cases:
        decision = decisions.get(case["claim"]["claim_id"])
        numeric = check_claim_numbers(case["claim"]["text"], list(case["sources"].values()))
        level, reasons = claim_level(decision, numeric)
        results.append(
            {
                **case,
                "decision": decision.model_dump() if decision else None,
                "numeric": numeric.model_dump(),
                "level": level,
                "reasons": reasons,
            }
        )
    return results, [usage for _, usage in outcomes]


def _report_claims(results: list[dict], usages: list, seconds: float, mode: str) -> None:
    print(f"\n{len(results)} claim cases, mode={mode}, {seconds:.1f}s wall")
    print(f"{'kind':18} {'n':>3}  {'none':>5} {'warn':>5} {'high':>5}   jev supported/contradicted/uncertain")
    for kind in ("real", "changed_number", "flipped_direction", "unrelated_source"):
        group = [r for r in results if r["kind"] == kind]
        if not group:
            continue
        levels = [sum(r["level"] == level for r in group) for level in ("none", "warning", "high")]
        jev = [sum((r["decision"] or {}).get("decision") == d for r in group) for d in ("supported", "contradicted", "uncertain")]
        print(f"{kind:18} {len(group):>3}  {levels[0]:>5} {levels[1]:>5} {levels[2]:>5}   {jev[0]}/{jev[1]}/{jev[2]}")
    real = [r for r in results if r["kind"] == "real"]
    negatives = [r for r in results if r["kind"] != "real"]
    flagged_answers = {r["question_number"] for r in real if r["level"] != "none"}
    print(f"\nreal claims with no signal: {sum(r['level'] == 'none' for r in real)}/{len(real)}")
    print(f"real claims marked high risk: {sum(r['level'] == 'high' for r in real)}/{len(real)}")
    print(f"negatives flagged (warning or high): {sum(r['level'] != 'none' for r in negatives)}/{len(negatives)}")
    print(f"answers with at least one warning: {len(flagged_answers)}/{len({r['question_number'] for r in real})}")
    tokens = sum(u.input_tokens for u in usages)
    latencies = sorted(u.seconds for u in usages)
    print(
        f"requests {len(usages)}, input tokens {tokens}, cost ${sum(u.cost_usd for u in usages):.5f}, "
        f"per-request latency median {latencies[len(latencies) // 2]:.2f}s max {latencies[-1]:.2f}s"
    )


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("runs", type=Path, nargs="+", help="smoke_assistant JSONL files")
    parser.add_argument("--unit", choices=["claim", "citation"], default="claim")
    parser.add_argument("--mode", choices=["batched", "isolated"], default="batched", help="--unit claim only")
    parser.add_argument("--max-positives", type=int, default=40, help="--unit citation only")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", type=Path, default=OUTPUT_DIR / f"judge-{datetime.now(UTC):%Y%m%d-%H%M%S}.jsonl")
    args = parser.parse_args()

    if args.unit == "claim":
        cases = build_claim_cases(load_claim_positives(args.runs), args.seed)
        print(f"{sum(c['kind'] == 'real' for c in cases)} real claims -> {len(cases)} cases", flush=True)
        started = time.perf_counter()
        results, usages = await run_claims(cases, batched=args.mode == "batched")
        _report_claims(results, usages, time.perf_counter() - started, args.mode)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text("".join(json.dumps(r) + "\n" for r in results))
        print(f"Wrote {args.out}")
        return

    positives = load_positives(args.runs)
    random.Random(args.seed).shuffle(positives)
    cases = build_cases(positives[: args.max_positives], args.seed)
    print(f"{min(len(positives), args.max_positives)} real citations -> {len(cases)} cases", flush=True)

    started = time.perf_counter()
    results = await run(cases)
    _report(results, time.perf_counter() - started)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(json.dumps(r) + "\n" for r in results))
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    asyncio.run(main())
