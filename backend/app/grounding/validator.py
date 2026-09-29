"""Deterministic, fail-closed checks that an answer stays inside the turn's evidence.

Everything here is string and id matching: it proves citation integrity (every marker
has a citation, every citation points at a chunk retrieved this turn, every excerpt is
really in that chunk, compared on words and numbers rather than typography or table
markup), not that the cited text semantically supports the claim.
"""

import re
import unicodedata
from typing import Literal

from pydantic import BaseModel

from app.assistant.deps import TurnRegistry
from app.assistant.outputs import GroundedAnswer

# "[1]" and "[1, 2]"; the instructions ask for the first, models sometimes write the second.
MARKER_RE = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")
# Money amounts and percentages: the claims an analyst would act on. Bare numbers and
# years are left out, they appear in too much non-factual text ("3 reasons", "fiscal 2024").
FIGURE_RE = re.compile(
    r"\$\s?\d[\d,]*(?:\.\d+)?(?:\s?(?:trillion|billion|million|thousand)\b)?"
    r"|\d[\d,]*(?:\.\d+)?\s?(?:%|percent\b)",
    re.IGNORECASE,
)
# Our search output marks cut excerpts with "..."; a model copying one keeps the dots.
EDGE_ELLIPSIS_RE = re.compile(r"^(?:\.\.\.|…)\s*|\s*(?:\.\.\.|…)$")
# Models often write typographic variants the filings do not use: gpt-oss emits U+2011
# (non-breaking hyphen) for every "-", which failed otherwise verbatim excerpts.
TYPOGRAPHY = str.maketrans(
    {
        "‘": "'",
        "’": "'",
        "“": '"',
        "”": '"',
        "\u2010": "-",  # hyphen
        "\u2011": "-",  # non-breaking hyphen
        "\u2012": "-",  # figure dash
        "–": "-",
        "—": "-",
        "\u2212": "-",  # minus sign
    }
)

# Markdown table markup is presentation, not evidence: a model that drops the "|---|"
# row or the pipes of a table row still quotes the same words and numbers in order.
TABLE_SEPARATOR_RE = re.compile(r"\|?(?:\s*:?-{3,}:?\s*\|)+")

MIN_EXCERPT_CHARS = 12  # shorter excerpts ("revenue", "2024") match almost any chunk

IssueCode = Literal[
    "empty_answer",
    "insufficient_evidence_with_citations",
    "missing_citations",
    "duplicate_citation_index",
    "citation_indices_not_contiguous",
    "marker_without_citation",
    "citation_not_referenced",
    "chunk_not_retrieved",
    "excerpt_too_short",
    "excerpt_not_in_chunk",
    "uncited_figure",
]


class ValidationIssue(BaseModel):
    code: IssueCode
    message: str
    severity: Literal["error", "warning"] = "error"
    citation_index: int | None = None


class ValidationResult(BaseModel):
    issues: list[ValidationIssue]

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def errors(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == "warning"]


def normalize_text(text: str) -> str:
    """Forgive what copying can change without changing meaning: unicode forms, curly
    quotes, hyphen and dash variants, and whitespace. Case, digits and words must match exactly."""
    text = unicodedata.normalize("NFKC", text).translate(TYPOGRAPHY)
    return " ".join(text.split())


def comparable_text(text: str) -> str:
    """normalize_text plus table markup removed; what excerpts and chunks are compared on."""
    text = TABLE_SEPARATOR_RE.sub(" ", normalize_text(text)).replace("|", " ")
    return " ".join(text.split())


def marker_indices(text: str) -> set[int]:
    return {int(number) for match in MARKER_RE.finditer(text) for number in match.group(1).split(",")}


def prune_unreferenced_citations(answer: GroundedAnswer) -> GroundedAnswer:
    """Drop citations the answer text never points to; they back no claim."""
    used = marker_indices(answer.answer)
    citations = [citation for citation in answer.citations if citation.citation_index in used]
    return answer.model_copy(update={"citations": citations})


def validate_grounded_answer(answer: GroundedAnswer, registry: TurnRegistry) -> ValidationResult:
    if not answer.answer.strip():
        return ValidationResult(issues=[ValidationIssue(code="empty_answer", message="The answer text is empty.")])

    if answer.insufficient_evidence:
        issues = _structure_issues(answer) if answer.citations else _marker_issues(answer)
        if answer.citations:
            issues.insert(
                0,
                ValidationIssue(
                    code="insufficient_evidence_with_citations",
                    message="An insufficient-evidence answer must not carry citations.",
                ),
            )
        return ValidationResult(issues=issues)

    if not answer.citations:
        return ValidationResult(
            issues=[
                ValidationIssue(
                    code="missing_citations",
                    message="A grounded answer needs at least one citation; otherwise it must be marked insufficient_evidence.",
                )
            ]
        )

    issues = _structure_issues(answer)
    issues += _citation_issues(answer, registry)
    issues += _figure_issues(answer)
    return ValidationResult(issues=issues)


def _marker_issues(answer: GroundedAnswer) -> list[ValidationIssue]:
    cited = {citation.citation_index for citation in answer.citations}
    used = marker_indices(answer.answer)
    issues = [
        ValidationIssue(
            code="marker_without_citation",
            message=f"[{index}] appears in the answer but no citation has that index.",
            citation_index=index,
        )
        for index in sorted(used - cited)
    ]
    issues += [
        ValidationIssue(
            code="citation_not_referenced",
            message=f"Citation {index} is never referenced as [{index}] in the answer.",
            citation_index=index,
        )
        for index in sorted(cited - used)
    ]
    return issues


def _structure_issues(answer: GroundedAnswer) -> list[ValidationIssue]:
    indices = [citation.citation_index for citation in answer.citations]
    issues = [
        ValidationIssue(
            code="duplicate_citation_index",
            message=f"Citation index {index} is used by more than one citation.",
            citation_index=index,
        )
        for index in sorted({index for index in indices if indices.count(index) > 1})
    ]
    if sorted(set(indices)) != list(range(1, len(set(indices)) + 1)):
        issues.append(
            ValidationIssue(
                code="citation_indices_not_contiguous",
                message=f"Citation indices must run 1..N without gaps, got {sorted(indices)}.",
            )
        )
    return issues + _marker_issues(answer)


def _citation_issues(answer: GroundedAnswer, registry: TurnRegistry) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for citation in answer.citations:
        index = citation.citation_index
        passage = registry.passages_by_chunk_id.get(citation.chunk_id)
        if passage is None:
            issues.append(
                ValidationIssue(
                    code="chunk_not_retrieved",
                    message=f"Chunk {citation.chunk_id} was not returned by any tool this turn.",
                    citation_index=index,
                )
            )
            continue

        excerpt = comparable_text(EDGE_ELLIPSIS_RE.sub("", citation.excerpt.strip()))
        if len(excerpt) < MIN_EXCERPT_CHARS:
            issues.append(
                ValidationIssue(
                    code="excerpt_too_short",
                    message=f"The excerpt {citation.excerpt!r} is shorter than {MIN_EXCERPT_CHARS} characters, too short to identify evidence.",
                    citation_index=index,
                )
            )
        elif excerpt not in comparable_text(passage.text):
            issues.append(
                ValidationIssue(
                    code="excerpt_not_in_chunk",
                    message=f"The excerpt is not a verbatim part of chunk {citation.chunk_id}.",
                    citation_index=index,
                )
            )
    return issues


def _figure_issues(answer: GroundedAnswer) -> list[ValidationIssue]:
    """A money amount or percentage on a line without any marker is an uncited claim.

    Lines rather than sentences: abbreviations ("U.S.", "vs.") make sentence splitting
    unreliable, and a wrong split would flag a properly cited figure. Whether a cited
    figure matches its sources is app/grounding/numeric.py's job.
    """
    issues: list[ValidationIssue] = []
    for line in answer.answer.splitlines():
        figures = list(FIGURE_RE.finditer(line))
        if figures and not MARKER_RE.search(line):
            issues.append(
                ValidationIssue(
                    code="uncited_figure",
                    message=f"{figures[0].group().strip()!r} is stated without any citation: {line.strip()!r}",
                )
            )
    return issues
