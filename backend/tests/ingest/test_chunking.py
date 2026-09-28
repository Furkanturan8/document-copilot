from types import SimpleNamespace

from ingest.chunk_and_embed import tables_from_records
from ingest.chunking import (
    ChunkRecord,
    base_chunk_metadata,
    narrative_text_without_tables,
    section_from_chunk,
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


def test_table_row_chunk_keeps_title_units_and_header_with_the_row():
    text = table_row_chunk_text(TABLE, TABLE.table_data["rows"][1])
    assert text.splitlines() == [
        "The following table shows net sales by category (dollars in millions):",
        "Units: in millions",
        "|  | 2024 | 2023 |",
        "|---|---|---|",
        "| Mac | 29,984 |  |",
    ]


def test_narrative_text_drops_markdown_table_lines():
    text = "Net sales grew.\n\n| | 2024 |\n|---|---|\n| iPhone | 201,183 |\nSee Note 2."
    assert narrative_text_without_tables(text) == "Net sales grew.\nSee Note 2."


def test_section_prefers_headings_then_item_reference():
    assert section_from_chunk(SimpleNamespace(headings=["Part II", "Item 7"]), "text") == "Part II > Item 7"
    assert section_from_chunk(SimpleNamespace(headings=None), "Item 1A. Risk Factors ...") == "Item 1A"
    assert section_from_chunk(SimpleNamespace(headings=None), "No section here") is None


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
