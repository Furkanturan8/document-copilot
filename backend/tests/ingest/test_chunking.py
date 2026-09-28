from types import SimpleNamespace

from docling_core.types.doc import DoclingDocument
from docling_core.types.doc.labels import DocItemLabel

from ingest.chunk_and_embed import tables_from_records
from ingest.chunking import (
    ChunkRecord,
    base_chunk_metadata,
    clean_chunk_text,
    document_positions,
    footer_page,
    item_heading,
    page_span,
    table_row_chunk_text,
    table_to_dict,
)
from ingest.sec_tables import ExtractedTable

TABLE = ExtractedTable(
    table_index=5,
    title="The following table shows net sales by category (dollars in millions):",
    units="in millions",
    markdown="| | 2024 | 2023 |\n|---|---|---|\n| iPhone | $201,183 | $200,583 |",
    table_data={
        "columns": ["", "2024", "2023"],
        "rows": [
            {"label": "iPhone", "values": ["$201,183", "$200,583"]},
            {"label": "Mac", "values": ["29,984", None]},
        ],
    },
    source_html_hash="abc",
)


def document(*texts: str) -> DoclingDocument:
    doc = DoclingDocument(name="filing")
    for text in texts:
        doc.add_text(label=DocItemLabel.TEXT, text=text)
    return doc


def test_table_row_chunk_keeps_title_units_and_header_with_the_row():
    text = table_row_chunk_text(TABLE, TABLE.table_data["rows"][1])
    assert text.splitlines() == [
        "The following table shows net sales by category (dollars in millions):",
        "Units: in millions",
        "|  | 2024 | 2023 |",
        "|---|---|---|",
        "| Mac | 29,984 |  |",
    ]


def test_footer_formats_of_each_filer():
    assert footer_page("35") == 35  # Microsoft, Amazon, NVIDIA
    assert footer_page("35.") == 35  # Alphabet
    assert footer_page("Apple Inc. | 2024 Form 10-K | 35") == 35
    assert footer_page("Net sales increased 35%") is None


def test_item_heading_uses_canonical_title_and_skips_toc_lines():
    assert item_heading("ITEM 1. B USINESS") == "Item 1. Business"
    assert item_heading("Item 1A. Risk Factors") == "Item 1A. Risk Factors"
    assert item_heading("Item 1A. Risk Factors 13") is None  # table of contents row
    assert item_heading("Item 99. Not a 10-K item") is None
    assert item_heading("As described in Item 7, revenue grew.") is None


def test_positions_follow_footers_and_headings():
    doc = document(
        "Cover page",
        "Item 1. Business",
        "We design smartphones.",
        "1",
        "Item 1A. Risk Factors",
        "Competition is intense.",
        "2",
    )
    positions, footers = document_positions(doc, table_refs={})
    by_text = {item.text: positions[item.self_ref] for item in doc.texts}

    assert by_text["Cover page"].page == "1" and by_text["Cover page"].section is None
    assert by_text["We design smartphones."].section == "Item 1. Business"
    assert by_text["Competition is intense."].page == "2"
    assert by_text["Competition is intense."].section == "Item 1A. Risk Factors"
    assert footers == {"1", "2"}


def test_table_of_contents_and_index_numbers_are_not_sections_or_pages():
    toc = []
    for code, title, page in [("1", "Business", "4"), ("1A", "Risk Factors", "13"), ("1B", "Staff", "31"),
                              ("2", "Properties", "32"), ("3", "Legal", "32"), ("4", "Mine Safety", "33")]:
        toc += [f"Item {code}.", title, page]
    doc = document(*toc, "Item 1. Business", "Body text of the business section.", "1")
    positions, footers = document_positions(doc, table_refs={})

    assert positions[doc.texts[1].self_ref].section is None  # inside the table of contents
    assert positions[doc.texts[-2].self_ref].section == "Item 1. Business"
    assert footers == {"1"}


def test_page_span_and_footer_cleanup():
    assert page_span("13", "14") == "13-14"
    assert page_span("13", "13") == "13"
    assert page_span(None, "7") == "7"
    text = "Revenue grew.\nApple Inc. | 2024 Form 10-K | 35\nTable of Contents\nMargins held."
    assert clean_chunk_text(text, {"Apple Inc. | 2024 Form 10-K | 35"}) == "Revenue grew.\nMargins held."


def test_base_metadata_copies_only_filing_fields():
    filing = {"ticker": "AAPL", "fiscal_year": 2024, "content_markdown": "huge"}
    metadata = base_chunk_metadata(filing)
    assert metadata["ticker"] == "AAPL" and metadata["fiscal_year"] == 2024
    assert "content_markdown" not in metadata


def test_one_document_table_per_table_index():
    def row_record(index: int) -> ChunkRecord:
        return ChunkRecord(index, "text", None, None, 10, {"chunk_kind": "table_row", "table": table_to_dict(TABLE)})

    narrative = ChunkRecord(0, "text", None, None, 10, {"chunk_kind": "narrative"})
    tables = tables_from_records(SimpleNamespace(id="doc-1"), [narrative, row_record(1), row_record(2)])

    assert len(tables) == 1
    assert tables[0].table_index == 5 and tables[0].document_id == "doc-1"
    assert tables[0].table_data == TABLE.table_data
