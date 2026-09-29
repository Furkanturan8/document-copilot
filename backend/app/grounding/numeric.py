"""Check a claim's figures against the numbers in its cited sources, in code.

Handles what a semantic judge gets wrong on financial tables: a figure restated in other
units ($25.0B for 24,967 in a millions table) and a percentage computed from two cited
numbers (a margin, a mix share, a growth rate, the rest of a share). Signs are ignored: filings write losses
as (924), answers as -$0.9B or "a loss of".
"""

import re
from itertools import permutations
from typing import Literal

from pydantic import BaseModel

FigureStatus = Literal["exact", "scaled", "derived", "unverified"]

CLAIM_FIGURE_RE = re.compile(
    r"(?<![\w.])(?P<dollar>\$)?\s?\(?(?P<number>\d[\d,]*(?:\.\d+)?)\)?\s?"
    r"(?P<unit>%|percent\b|trillion\b|billion\b|million\b|thousand\b|[TBMK]\b)?"
)
SOURCE_NUMBER_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")
FORM_NAME_RE = re.compile(r"\b10-[KQ]\b")
UNIT_SCALE = {
    "trillion": 1e12,
    "t": 1e12,
    "billion": 1e9,
    "b": 1e9,
    "million": 1e6,
    "m": 1e6,
    "thousand": 1e3,
    "k": 1e3,
}
SOURCE_SCALES = (1, 1e3, 1e6, 1e9)  # tables state amounts as-is, in thousands, millions or billions
MAX_SOURCE_NUMBERS = 200  # bounds the pairwise search for derived percentages


class FigureCheck(BaseModel):
    figure: str
    status: FigureStatus


class NumericCheck(BaseModel):
    figures: list[FigureCheck]

    @property
    def unverified(self) -> list[str]:
        return [check.figure for check in self.figures if check.status == "unverified"]

    @property
    def all_verified(self) -> bool:
        """True only when there were figures to check and every one of them matched."""
        return bool(self.figures) and not self.unverified


def _decimals(number: str) -> int:
    return len(number.split(".")[1]) if "." in number else 0


def _close(value: float, target: float, decimals: int) -> bool:
    return abs(round(value, decimals) - target) < 10**-decimals / 2


def _claim_figures(text: str) -> list[tuple[str, float, int, str | None, bool]]:
    """(raw, value, decimals, unit, is_money) for figures worth checking: amounts,
    percentages and formatted numbers, not years, counts or form names."""
    figures = []
    for match in CLAIM_FIGURE_RE.finditer(FORM_NAME_RE.sub(" ", text)):
        number, unit, dollar = match.group("number"), match.group("unit"), match.group("dollar")
        formatted = "," in number or "." in number
        if not (unit or dollar or formatted):
            continue
        value = float(number.replace(",", ""))
        figures.append((match.group().strip(), value, _decimals(number), unit.lower() if unit else None, bool(dollar)))
    return figures


def _source_numbers(sources: list[str]) -> list[float]:
    values = {float(raw.replace(",", "")) for text in sources for raw in SOURCE_NUMBER_RE.findall(text)}
    return sorted(value for value in values if value > 0)[:MAX_SOURCE_NUMBERS]


def _check_percent(value: float, decimals: int, numbers: list[float]) -> FigureStatus:
    if any(_close(n, value, decimals) for n in numbers):
        return "exact"
    # "48% U.S. / 52% non-U.S.": the rest of a share the sources state.
    if any(_close(100 - n, value, decimals) for n in numbers if n < 100):
        return "derived"
    # An integer percentage is matched by too many random pairs to count as evidence.
    if decimals == 0:
        return "unverified"
    for a, b in permutations(numbers, 2):
        if _close(a / b * 100, value, decimals) or _close(abs(a - b) / b * 100, value, decimals):
            return "derived"
    return "unverified"


def _check_amount(value: float, decimals: int, unit: str | None, numbers: list[float]) -> FigureStatus:
    claim_scale = UNIT_SCALE.get(unit, 1) if unit else 1
    for number in numbers:
        if _close(number, value, decimals) and claim_scale == 1:
            return "exact"
        if any(_close(number * scale / claim_scale, value, decimals) for scale in SOURCE_SCALES):
            return "scaled"
    return "unverified"


def check_claim_numbers(claim_text: str, sources: list[str]) -> NumericCheck:
    numbers = _source_numbers(sources)
    checks = []
    for raw, value, decimals, unit, _ in _claim_figures(claim_text):
        if unit in ("%", "percent"):
            status = _check_percent(value, decimals, numbers)
        else:
            status = _check_amount(value, decimals, unit, numbers)
        checks.append(FigureCheck(figure=raw, status=status))
    return NumericCheck(figures=checks)
