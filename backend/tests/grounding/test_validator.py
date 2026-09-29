import uuid

from app.assistant.deps import TurnRegistry
from app.assistant.outputs import Citation, GroundedAnswer
from app.grounding.validator import (
    prune_unreferenced_citations,
    validate_grounded_answer,
)
from tests.assistant.test_tools import _passage

REVENUE = _passage(
    "Data Center revenue for fiscal year 2024 was $47.5 billion, up 217% from a year ago. "
    "Strong demand was driven by the NVIDIA Hopper GPU computing platform."
)
MARGIN = _passage("Gross margin increased to 72.7% from 56.9% in fiscal year 2023.")


def _registry(*passages) -> TurnRegistry:
    registry = TurnRegistry()
    registry.register(list(passages))
    return registry


def _answer(text: str, *citations: tuple[int, uuid.UUID, str], insufficient: bool = False) -> GroundedAnswer:
    return GroundedAnswer(
        answer=text,
        citations=[Citation(citation_index=i, chunk_id=c, excerpt=e) for i, c, e in citations],
        insufficient_evidence=insufficient,
    )


def _codes(result) -> list[str]:
    return [issue.code for issue in result.issues]


VALID = _answer(
    "Data Center revenue reached $47.5 billion [1], and gross margin rose to 72.7% [2].",
    (1, REVENUE.chunk_id, "Data Center revenue for fiscal year 2024 was $47.5 billion"),
    (2, MARGIN.chunk_id, "Gross margin increased to 72.7% from 56.9%"),
)


# --- What it accepts ------------------------------------------------------------------


def test_valid_answer_passes_without_issues():
    result = validate_grounded_answer(VALID, _registry(REVENUE, MARGIN))

    assert result.ok and result.issues == []


def test_insufficient_evidence_without_citations_passes():
    answer = _answer("The filings do not break out generative AI margins.", insufficient=True)

    assert validate_grounded_answer(answer, TurnRegistry()).ok


def test_excerpt_matching_forgives_whitespace_quotes_dashes_and_cut_marks():
    source = _passage("Apple’s net sales  grew\n— driven by iPhone — in fiscal 2024 and beyond.")
    answer = _answer(
        "Net sales grew [1].",
        (1, source.chunk_id, "...Apple's net sales grew - driven by iPhone - in fiscal 2024..."),
    )

    assert validate_grounded_answer(answer, _registry(source)).ok


def test_excerpt_matching_forgives_non_breaking_hyphens():
    # Seen with gpt-oss: "AI-enabled" in the filing, "AI\u2011enabled" in the excerpt.
    source = _passage("Startups use our platforms to build new generative and agentic AI-enabled products.")
    answer = _answer(
        "Startups build AI products [1].",
        (1, source.chunk_id, "build new generative and agentic AI\u2011enabled products"),
    )

    assert validate_grounded_answer(answer, _registry(source)).ok


def test_excerpt_stitched_from_separate_passages_fails():
    # Also seen with gpt-oss: three sentences joined with an ellipsis into one "quote".
    source = _passage("Trends put pressure on our margins. Other text here. AI could affect our monetization trends.")
    answer = _answer(
        "AI may pressure margins [1].",
        (1, source.chunk_id, "put pressure on our margins. … AI could affect our monetization trends."),
    )

    assert _codes(validate_grounded_answer(answer, _registry(source))) == ["excerpt_not_in_chunk"]


def test_table_excerpt_without_markdown_separator_row_passes():
    # Seen with gpt-oss: the "|---|" row between header and data was dropped.
    table = _passage(
        "INCOME STATEMENTS | Year Ended June 30, | 2025 | 2024 | 2023 |\n|---|---|---|---|\n"
        "| Gross margin | 193,893 | 171,008 | 146,052 |"
    )
    answer = _answer(
        "Gross margin grew [1].",
        (1, table.chunk_id, "Year Ended June 30, | 2025 | 2024 | 2023 | | Gross margin | 193,893 | 171,008 | 146,052"),
    )

    assert validate_grounded_answer(answer, _registry(table)).ok


def test_table_excerpt_with_a_changed_number_still_fails():
    table = _passage("| Gross margin | 193,893 | 171,008 |\n|---|---|---|")
    answer = _answer("Gross margin grew [1].", (1, table.chunk_id, "Gross margin | 193,893 | 171,009"))

    assert _codes(validate_grounded_answer(answer, _registry(table))) == ["excerpt_not_in_chunk"]


def test_a_neighbor_returned_with_a_hit_is_citable():
    neighbor = _passage("Compute revenue grew as hyperscalers expanded capacity.")
    hit = _passage("Data Center overview.", neighbors=[neighbor])
    answer = _answer("Compute grew [1].", (1, neighbor.chunk_id, "Compute revenue grew as hyperscalers"))

    assert validate_grounded_answer(answer, _registry(hit)).ok


def test_grouped_markers_count_as_references():
    answer = _answer(
        "Revenue and margin both rose [1, 2].",
        (1, REVENUE.chunk_id, "Data Center revenue for fiscal year 2024"),
        (2, MARGIN.chunk_id, "Gross margin increased to 72.7%"),
    )

    assert validate_grounded_answer(answer, _registry(REVENUE, MARGIN)).ok


def test_abbreviations_do_not_split_a_cited_claim():
    source = _passage("U.S. revenue was $12.1 billion vs. $9.8 billion in the prior year.")
    answer = _answer(
        "U.S. revenue was $12.1 billion vs. $9.8 billion a year earlier [1].",
        (1, source.chunk_id, "U.S. revenue was $12.1 billion vs. $9.8 billion"),
    )

    assert validate_grounded_answer(answer, _registry(source)).issues == []


# --- What it rejects ------------------------------------------------------------------


def test_empty_answer_fails():
    assert _codes(validate_grounded_answer(_answer("  "), TurnRegistry())) == ["empty_answer"]


def test_answer_without_citations_must_be_marked_insufficient():
    result = validate_grounded_answer(_answer("Revenue grew strongly."), TurnRegistry())

    assert _codes(result) == ["missing_citations"]


def test_insufficient_evidence_with_citations_fails():
    answer = _answer(
        "Not enough evidence [1].", (1, REVENUE.chunk_id, "Data Center revenue for fiscal"), insufficient=True
    )

    assert "insufficient_evidence_with_citations" in _codes(validate_grounded_answer(answer, _registry(REVENUE)))


def test_insufficient_evidence_with_a_dangling_marker_fails():
    answer = _answer("Revenue is discussed elsewhere [1].", insufficient=True)

    assert _codes(validate_grounded_answer(answer, TurnRegistry())) == ["marker_without_citation"]


def test_chunk_that_was_never_retrieved_fails():
    unseen = _passage("Data Center revenue for fiscal year 2024 was $47.5 billion.")
    answer = _answer("Revenue was $47.5 billion [1].", (1, unseen.chunk_id, "Data Center revenue for fiscal year 2024"))

    result = validate_grounded_answer(answer, _registry(REVENUE))

    assert _codes(result) == ["chunk_not_retrieved"]
    assert result.issues[0].citation_index == 1


def test_paraphrased_excerpt_fails():
    answer = _answer(
        "Revenue was $47.5 billion [1].", (1, REVENUE.chunk_id, "Data Center sales in 2024 were $47.5 billion")
    )

    assert _codes(validate_grounded_answer(answer, _registry(REVENUE))) == ["excerpt_not_in_chunk"]


def test_excerpt_copied_from_the_wrong_chunk_fails():
    answer = _answer("Margin rose to 72.7% [1].", (1, REVENUE.chunk_id, "Gross margin increased to 72.7%"))

    result = validate_grounded_answer(answer, _registry(REVENUE, MARGIN))

    assert "excerpt_not_in_chunk" in _codes(result)


def test_changed_number_in_excerpt_fails():
    answer = _answer("Revenue was $48.5 billion [1].", (1, REVENUE.chunk_id, "fiscal year 2024 was $48.5 billion"))

    assert "excerpt_not_in_chunk" in _codes(validate_grounded_answer(answer, _registry(REVENUE)))


def test_trivially_short_excerpt_fails():
    answer = _answer("Revenue grew [1].", (1, REVENUE.chunk_id, "revenue"))

    assert _codes(validate_grounded_answer(answer, _registry(REVENUE))) == ["excerpt_too_short"]


def test_marker_without_citation_and_unreferenced_citation_both_fail():
    answer = _answer("Revenue grew [2].", (1, REVENUE.chunk_id, "Data Center revenue for fiscal year 2024"))

    result = validate_grounded_answer(answer, _registry(REVENUE))

    assert _codes(result) == ["marker_without_citation", "citation_not_referenced"]
    assert [issue.citation_index for issue in result.issues] == [2, 1]


def test_duplicate_and_gapped_citation_indices_fail():
    answer = _answer(
        "Revenue [1] and margin [1] and more [3].",
        (1, REVENUE.chunk_id, "Data Center revenue for fiscal year 2024"),
        (1, MARGIN.chunk_id, "Gross margin increased to 72.7%"),
        (3, MARGIN.chunk_id, "Gross margin increased to 72.7%"),
    )

    codes = _codes(validate_grounded_answer(answer, _registry(REVENUE, MARGIN)))

    assert "duplicate_citation_index" in codes and "citation_indices_not_contiguous" in codes


def test_money_or_percentage_on_a_line_without_any_marker_fails():
    answer = _answer(
        "Data Center revenue grew [1].\nGross margin reached 72.7% in fiscal 2024.",
        (1, REVENUE.chunk_id, "Data Center revenue for fiscal year 2024"),
    )

    result = validate_grounded_answer(answer, _registry(REVENUE))

    assert _codes(result) == ["uncited_figure"]
    assert not result.ok


def test_all_problems_are_reported_together():
    answer = _answer(
        "Revenue was $47.5 billion [1] and margin 72.7% [2].",
        (1, uuid.uuid4(), "Data Center revenue for fiscal year 2024"),
        (2, MARGIN.chunk_id, "Margins went up a lot"),
    )

    result = validate_grounded_answer(answer, _registry(REVENUE, MARGIN))

    assert _codes(result) == ["chunk_not_retrieved", "excerpt_not_in_chunk"]


# --- Warnings: reported, but the answer still passes ----------------------------------


def test_figure_missing_from_its_cited_chunk_is_a_warning_not_a_failure():
    answer = _answer(
        "Revenue roughly tripled to $47.5 billion, a 3.2% share [1].",
        (1, REVENUE.chunk_id, "Data Center revenue for fiscal year 2024 was $47.5 billion"),
    )

    result = validate_grounded_answer(answer, _registry(REVENUE))

    assert result.ok
    assert [(w.code, w.citation_index) for w in result.warnings] == [("figure_not_in_cited_chunks", 1)]
    assert "3.2%" in result.warnings[0].message


def test_figure_formats_are_compared_by_number():
    table = _passage("| Revenue | $ 60,922 | $ 26,974 |")
    answer = _answer("Revenue was $60,922 million [1].", (1, table.chunk_id, "| Revenue | $ 60,922 |"))

    assert validate_grounded_answer(answer, _registry(table)).issues == []


# --- Known limits: these pass although a careful reader would object -----------------


def test_limit_a_real_excerpt_does_not_prove_the_claim():
    # The excerpt is verbatim, but the answer says the opposite of the source.
    answer = _answer(
        "Data Center revenue declined in fiscal 2024 [1].",
        (1, REVENUE.chunk_id, "Data Center revenue for fiscal year 2024"),
    )

    assert validate_grounded_answer(answer, _registry(REVENUE)).ok


def test_limit_uncited_claims_without_money_or_percent_are_not_detected():
    answer = _answer(
        "Revenue grew [1]. NVIDIA also plans to exit the gaming market.",
        (1, REVENUE.chunk_id, "Data Center revenue for fiscal year 2024"),
    )

    assert validate_grounded_answer(answer, _registry(REVENUE)).ok


def test_limit_a_cited_line_covers_its_other_sentences():
    # Line-level checking: the uncited second sentence shares the line with a marker.
    answer = _answer(
        "Revenue was $47.5 billion [1]. Operating income was $32.9 billion.",
        (1, REVENUE.chunk_id, "Data Center revenue for fiscal year 2024 was $47.5 billion"),
    )

    result = validate_grounded_answer(answer, _registry(REVENUE))

    assert result.ok and [w.code for w in result.warnings] == ["figure_not_in_cited_chunks"]


# --- Pruning ----------------------------------------------------------------------------


def test_prune_drops_only_citations_the_text_never_references():
    answer = _answer(
        "Revenue grew [1].",
        (1, REVENUE.chunk_id, "Data Center revenue for fiscal year 2024"),
        (2, MARGIN.chunk_id, "Gross margin increased to 72.7%"),
    )

    pruned = prune_unreferenced_citations(answer)

    assert [c.citation_index for c in pruned.citations] == [1]
    assert validate_grounded_answer(pruned, _registry(REVENUE, MARGIN)).ok
