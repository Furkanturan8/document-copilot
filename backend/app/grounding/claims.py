"""Answer text -> claims: each cited sentence or table row, with every citation it relies on."""

import re

from pydantic import BaseModel

from app.grounding.validator import MARKER_RE, marker_indices

# Sentence ends inside a paragraph; lines are split first, so table rows and bullets stay whole.
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z*(\[])")
# Kept for the per-citation benchmark in judge.py: sentence ends and line breaks.
SEGMENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z*(\[])|\n")
TABLE_SEPARATOR_LINE_RE = re.compile(r"^\|?(?:\s*:?-{3,}:?\s*\|)+\s*$")


class Claim(BaseModel):
    claim_id: str
    text: str  # markers removed
    context: str | None = None  # a table row's header row, so its cells have names
    citation_indices: list[int]  # every source the claim cites, judged together


def clean_claim_text(text: str) -> str:
    text = " ".join(MARKER_RE.sub("", text).split())
    text = re.sub(r"\s+([.,;:])", r"\1", text)
    return re.sub(r"^(?:[,;:|\-]\s*|and\s+)+", "", text).strip()


def _units(answer_text: str) -> list[tuple[str, str | None]]:
    """(text, context) pairs: sentences of prose lines, and table rows with their header."""
    lines = answer_text.splitlines()
    units: list[tuple[str, str | None]] = []
    header: str | None = None
    for position, line in enumerate(lines):
        if not line.lstrip().startswith("|"):
            header = None
            units += [(sentence, None) for sentence in SENTENCE_SPLIT_RE.split(line)]
        elif TABLE_SEPARATOR_LINE_RE.match(line.strip()):
            continue
        elif position + 1 < len(lines) and TABLE_SEPARATOR_LINE_RE.match(lines[position + 1].strip()):
            header = clean_claim_text(line)
        else:
            units.append((line, header))
    return units


def split_claims(answer_text: str) -> list[Claim]:
    claims: list[Claim] = []
    seen: set[tuple[str, tuple[int, ...]]] = set()
    for unit, context in _units(answer_text):
        indices = tuple(sorted(marker_indices(unit)))
        text = clean_claim_text(unit)
        if not indices or not text or (text, indices) in seen:
            continue
        seen.add((text, indices))
        claims.append(
            Claim(claim_id=f"c{len(claims) + 1}", text=text, context=context, citation_indices=list(indices))
        )
    return claims
