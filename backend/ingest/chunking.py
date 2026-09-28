"""Split an SEC filing into retrieval chunks.

Narrative text comes from Docling's HybridChunker (token-aware, max CHUNK_MAX_TOKENS).
Docling's own tables mirror the HTML layout grid (repeated colspan cells, "$" and "%" in
their own cells), so they never reach the index as is:

- A Docling table that matches a clean table from ingest/sec_tables.py is serialized as a
  small marker. Where the marker lands in a chunk, that table's "table_row" chunks are
  emitted instead (title + units + header + one row), so figures keep their labels and
  their place in the document, and a large table split over several Docling chunks is
  not indexed twice.
- Any other table is layout (bullets, footnotes, headings, cover page) and is flattened
  to plain text.

Page and section are computed on the whole document before chunking, because a single
chunk rarely contains the evidence: a page footer ends each page, and an "Item N." heading
opens each section.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tiktoken
from docling.chunking import HybridChunker
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter
from docling_core.transforms.chunker.hierarchical_chunker import (
    ChunkingDocSerializer,
    ChunkingSerializerProvider,
)
from docling_core.transforms.chunker.tokenizer.openai import OpenAITokenizer
from docling_core.transforms.serializer.base import (
    BaseDocSerializer,
    BaseTableSerializer,
    SerializationResult,
)
from docling_core.transforms.serializer.common import create_ser_result
from docling_core.types.doc import DoclingDocument, TableItem, TextItem

from ingest.sec_tables import ExtractedTable, extract_sec_tables

CHUNK_MAX_TOKENS = 512
DOWNLOADS_DIR = Path(__file__).resolve().parents[2] / "data" / "downloads"
MANIFEST_PATH = DOWNLOADS_DIR / "manifest.json"

TABLE_MARKER = "[[table:{index}]]"
TABLE_MARKER_RE = re.compile(r"\[\[table:(\d+)\]\]")
NUMBER_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")

# Page footers, one per page: "35" (Microsoft, Amazon, NVIDIA), "35." (Alphabet),
# "Apple Inc. | 2024 Form 10-K | 35" (Apple).
FOOTER_RES = (
    re.compile(r"^(\d{1,3})\.?$"),
    re.compile(r"\|\s*\d{4} Form 10-K\s*\|\s*(\d{1,3})$", re.IGNORECASE),
)
RUNNING_HEADER_RE = re.compile(r"^table of contents\b", re.IGNORECASE)
ITEM_HEADING_RE = re.compile(r"^\s*item\s+(\d{1,2}[a-c]?)\b", re.IGNORECASE)
TOC_PAGE_SUFFIX_RE = re.compile(r"\s\d{1,3}$")
HEADING_MAX_LENGTH = 200
# Tables of contents and indexes list their entries a few items apart.
LISTING_MAX_GAP = 3
TOC_RUN_LENGTH = 5
FOOTER_LISTING_RUN_LENGTH = 3

# Form 10-K item titles are fixed by the SEC, so sections use the canonical title rather
# than each filer's rendering ("ITEM 1. B USINESS", "Item 1. Business").
ITEM_TITLES = {
    "1": "Business",
    "1A": "Risk Factors",
    "1B": "Unresolved Staff Comments",
    "1C": "Cybersecurity",
    "2": "Properties",
    "3": "Legal Proceedings",
    "4": "Mine Safety Disclosures",
    "5": "Market for Registrant's Common Equity, Related Stockholder Matters and Issuer Purchases of Equity Securities",
    "6": "[Reserved]",
    "7": "Management's Discussion and Analysis of Financial Condition and Results of Operations",
    "7A": "Quantitative and Qualitative Disclosures About Market Risk",
    "8": "Financial Statements and Supplementary Data",
    "9": "Changes in and Disagreements with Accountants on Accounting and Financial Disclosure",
    "9A": "Controls and Procedures",
    "9B": "Other Information",
    "9C": "Disclosure Regarding Foreign Jurisdictions that Prevent Inspections",
    "10": "Directors, Executive Officers and Corporate Governance",
    "11": "Executive Compensation",
    "12": "Security Ownership of Certain Beneficial Owners and Management and Related Stockholder Matters",
    "13": "Certain Relationships and Related Transactions, and Director Independence",
    "14": "Principal Accountant Fees and Services",
    "15": "Exhibits and Financial Statement Schedules",
    "16": "Form 10-K Summary",
}


@dataclass(frozen=True)
class ChunkRecord:
    chunk_index: int
    text: str
    page: str | None
    section: str | None
    token_count: int
    chunk_metadata: dict[str, Any]


@dataclass(frozen=True)
class Position:
    page: str | None
    section: str | None


NO_POSITION = Position(None, None)


def page_span(start: str | None, end: str | None) -> str | None:
    """"13" for a chunk on one page, "13-14" for one that crosses a page break."""
    if start and end and start != end:
        return f"{start}-{end}"
    return start or end


class PatchedOpenAITokenizer(OpenAITokenizer):
    """Counts tokens without rejecting text that happens to contain tiktoken special tokens."""

    def count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text, allowed_special=set(), disallowed_special=()))


def layout_table_text(item: TableItem) -> str:
    """Flatten a layout table to plain lines: each cell once, empty cells and running headers dropped."""
    lines = []
    for row in item.data.grid:
        seen: set[int] = set()
        cells = []
        for cell in row:
            # A spanning cell appears in every grid column it covers; keep it once.
            if id(cell) in seen or not cell.text.strip():
                continue
            seen.add(id(cell))
            cells.append(" ".join(cell.text.split()))
        line = " ".join(cells)
        if line and not RUNNING_HEADER_RE.match(line):
            lines.append(line)
    return "\n".join(lines)


class SecTableSerializer(BaseTableSerializer):
    def __init__(self, table_refs: dict[str, int]) -> None:
        self.table_refs = table_refs

    def serialize(
        self, *, item: TableItem, doc_serializer: BaseDocSerializer, doc: DoclingDocument, **kwargs: Any
    ) -> SerializationResult:
        index = self.table_refs.get(item.self_ref)
        text = TABLE_MARKER.format(index=index) if index is not None else layout_table_text(item)
        return create_ser_result(text=text, span_source=item)


class SecSerializerProvider(ChunkingSerializerProvider):
    def __init__(self, table_refs: dict[str, int]) -> None:
        self._table_refs = table_refs

    def get_serializer(self, doc: DoclingDocument) -> ChunkingDocSerializer:
        return ChunkingDocSerializer(doc=doc, table_serializer=SecTableSerializer(self._table_refs))


def build_hybrid_chunker(table_refs: dict[str, int] | None = None, max_tokens: int = CHUNK_MAX_TOKENS) -> HybridChunker:
    tokenizer = PatchedOpenAITokenizer(tokenizer=tiktoken.get_encoding("cl100k_base"), max_tokens=max_tokens)
    return HybridChunker(
        tokenizer=tokenizer,
        merge_peers=True,
        serializer_provider=SecSerializerProvider(table_refs or {}),
    )


def convert_html_to_document(html_path: Path) -> DoclingDocument:
    return DocumentConverter(allowed_formats=[InputFormat.HTML]).convert(html_path).document


def html_path_for_accession(accession_number: str) -> Path:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    for filing in manifest["filings"]:
        if filing["accession_number"] == accession_number:
            return DOWNLOADS_DIR / filing["local_path"]
    raise KeyError(f"Accession {accession_number} is not in {MANIFEST_PATH}")


def base_chunk_metadata(filing: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "ticker",
        "cik",
        "company_name",
        "form",
        "filing_date",
        "report_date",
        "fiscal_year",
        "accession_number",
        "primary_document",
        "source_url",
    )
    return {key: filing.get(key) for key in keys}


def _numbers(texts: list[str]) -> set[str]:
    return {number for text in texts for number in NUMBER_RE.findall(text)}


def match_tables(doc: DoclingDocument, tables: list[ExtractedTable]) -> dict[str, int]:
    """Map Docling table refs to the clean table with the same figures.

    Both lists are in document order, so matching walks forward; a Docling table without
    a clean counterpart (layout) is simply skipped.
    """
    matches: dict[str, int] = {}
    next_table = 0
    for item in doc.tables:
        docling_numbers = _numbers([cell.text for cell in item.data.table_cells])
        for index in range(next_table, min(next_table + 3, len(tables))):
            rows = tables[index].table_data["rows"]
            clean_numbers = _numbers([value for row in rows for value in row["values"] if value])
            if clean_numbers and len(clean_numbers & docling_numbers) >= 0.8 * len(clean_numbers):
                matches[item.self_ref] = index
                next_table = index + 1
                break
    return matches


def footer_page(text: str) -> int | None:
    for pattern in FOOTER_RES:
        match = pattern.search(text.strip())
        if match:
            return int(match.group(1))
    return None


def item_heading(line: str) -> str | None:
    match = ITEM_HEADING_RE.match(line)
    if not match or len(line) > HEADING_MAX_LENGTH or TOC_PAGE_SUFFIX_RE.search(line.strip()):
        return None
    code = match.group(1).upper()
    return f"Item {code}. {ITEM_TITLES[code]}" if code in ITEM_TITLES else None


def document_positions(doc: DoclingDocument, table_refs: dict[str, int]) -> tuple[dict[str, Position], set[str]]:
    """Page and section of every item, plus the texts of the page footers found.

    A footer closes its page, so an item's page is the next footer after it. Footers must
    count upwards, which keeps stray numbers in the text from being taken for one.
    """
    items: list[tuple[str, list[str], bool]] = []  # ref, lines, is a text item
    for item, _ in doc.iterate_items():
        if isinstance(item, TableItem):
            lines = [] if item.self_ref in table_refs else layout_table_text(item).splitlines()
            items.append((item.self_ref, lines, False))
        elif isinstance(item, TextItem):
            items.append((item.self_ref, [item.text], True))

    candidates: dict[int, int] = {}
    for position, (_, lines, is_text) in enumerate(items):
        page = footer_page(lines[0]) if is_text and lines else None
        if page is not None:
            candidates[position] = page
    # Page numbers listed in a table of contents or financial statement index come a few
    # items apart; real footers have a page of content between them.
    for position in _dense_runs(sorted(candidates), min_length=FOOTER_LISTING_RUN_LENGTH, orders=candidates):
        del candidates[position]

    footer_at: dict[int, int] = {}
    last_page = 0
    for position, page in sorted(candidates.items()):
        if last_page < page <= last_page + 3:
            footer_at[position] = page
            last_page = page
    footers = {items[position][1][0].strip() for position in footer_at}

    pages: list[int | None] = [None] * len(items)
    next_page = None
    for position in range(len(items) - 1, -1, -1):
        next_page = footer_at.get(position, next_page)
        pages[position] = next_page

    headings: dict[int, str] = {}
    for position, (_, lines, _) in enumerate(items):
        for line in lines:
            heading = item_heading(line)
            if heading:
                headings[position] = heading
    # A table of contents lists "Item N." lines back to back in ascending order; real sections
    # have body text between their headings, and "Item 1." after the list starts a new run.
    item_order = {code: order for order, code in enumerate(ITEM_TITLES)}
    orders = {position: item_order[heading.split()[1].rstrip(".")] for position, heading in headings.items()}
    for position in _dense_runs(sorted(headings), min_length=TOC_RUN_LENGTH, orders=orders):
        del headings[position]

    positions: dict[str, Position] = {}
    section = None
    for position, (ref, _, _) in enumerate(items):
        section = headings.get(position, section)
        page = pages[position]
        positions[ref] = Position(str(page) if page is not None else None, section)
    return positions, footers


def _dense_runs(positions: list[int], *, min_length: int, orders: dict[int, int] | None = None) -> set[int]:
    """Positions in a run of at least `min_length`, each within LISTING_MAX_GAP items of the next.

    With `orders`, a run also breaks where the order stops increasing.
    """
    runs: list[list[int]] = []
    for position in positions:
        previous = runs[-1][-1] if runs else None
        if (
            previous is not None
            and position - previous <= LISTING_MAX_GAP
            and (orders is None or orders[position] > orders[previous])
        ):
            runs[-1].append(position)
        else:
            runs.append([position])
    return {position for run in runs if len(run) >= min_length for position in run}


def clean_chunk_text(text: str, footers: set[str]) -> str:
    return "\n".join(
        line
        for line in text.splitlines()
        if line.strip() and line.strip() not in footers and not RUNNING_HEADER_RE.match(line.strip())
    )


def table_to_dict(table: ExtractedTable) -> dict[str, Any]:
    return {
        "table_index": table.table_index,
        "title": table.title,
        "units": table.units,
        "markdown": table.markdown,
        "table_data": table.table_data,
        "source_html_hash": table.source_html_hash,
    }


def table_row_chunk_text(table: ExtractedTable, row: dict[str, Any]) -> str:
    columns = table.table_data["columns"]
    lines = [table.title or f"Table {table.table_index + 1}"]
    if table.units:
        lines.append(f"Units: {table.units}")
    lines.append("| " + " | ".join(columns) + " |")
    lines.append("|" + "---|" * len(columns))
    lines.append("| " + " | ".join([row["label"], *(value or "" for value in row["values"])]) + " |")
    return "\n".join(lines)


def chunk_document(html_path: Path, filing: dict[str, Any], *, max_chunks: int | None = None) -> list[ChunkRecord]:
    """Return the ordered chunk records of one filing.

    `filing` carries the document metadata copied onto every chunk (see base_chunk_metadata).
    """
    tables = extract_sec_tables(html_path.read_text(encoding="utf-8", errors="replace"))
    document = convert_html_to_document(html_path)
    table_refs = match_tables(document, tables)
    positions, footers = document_positions(document, table_refs)
    table_positions = {index: positions[ref] for ref, index in table_refs.items()}

    chunker = build_hybrid_chunker(table_refs)
    count_tokens = chunker.tokenizer.count_tokens
    base = base_chunk_metadata(filing)
    records: list[ChunkRecord] = []
    used_tables: set[int] = set()

    def add_narrative(text: str, position: Position, meta: Any) -> None:
        records.append(
            ChunkRecord(
                chunk_index=len(records),
                text=text,
                page=position.page,
                section=position.section,
                token_count=count_tokens(text),
                chunk_metadata={**base, "chunk_kind": "narrative", "docling_meta": meta.export_json_dict()},
            )
        )

    def add_table_rows(table: ExtractedTable, position: Position) -> None:
        for row in table.table_data["rows"]:
            text = table_row_chunk_text(table, row)
            records.append(
                ChunkRecord(
                    chunk_index=len(records),
                    text=text,
                    page=position.page,
                    section=position.section,
                    token_count=count_tokens(text),
                    chunk_metadata={
                        **base,
                        "chunk_kind": "table_row",
                        "table_index": table.table_index,
                        "table_title": table.title,
                        "row_label": row["label"],
                        # The whole table rides along: the chunking stage builds document_tables
                        # from it, and a citation can show the full table around its row.
                        "table": table_to_dict(table),
                    },
                )
            )
        used_tables.add(table.table_index)

    for index, chunk in enumerate(chunker.chunk(dl_doc=document)):
        if max_chunks is not None and index >= max_chunks:
            break
        text = clean_chunk_text(chunker.contextualize(chunk=chunk), footers)
        refs = [item.self_ref for item in chunk.meta.doc_items or []]
        start = positions.get(refs[0], NO_POSITION) if refs else NO_POSITION
        end = positions.get(refs[-1], NO_POSITION) if refs else NO_POSITION
        position = Position(page_span(start.page, end.page), start.section)

        # Split the chunk at table markers: narrative before a marker, then that table's rows.
        cursor = 0
        for marker in TABLE_MARKER_RE.finditer(text):
            before = text[cursor : marker.start()].strip()
            if before:
                add_narrative(before, position, chunk.meta)
            table_index = int(marker.group(1))
            table_position = table_positions[table_index]
            if table_index not in used_tables:
                add_table_rows(tables[table_index], table_position)
            position = Position(page_span(table_position.page, end.page), table_position.section)
            cursor = marker.end()
        rest = text[cursor:].strip()
        if rest:
            add_narrative(rest, position, chunk.meta)

    # Clean tables Docling did not produce a matching table for still belong in the index.
    if max_chunks is None:
        for table in tables:
            if table.table_index not in used_tables:
                add_table_rows(table, NO_POSITION)
    return records
