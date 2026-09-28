"""Split an SEC filing into retrieval chunks.

Narrative text comes from Docling's HybridChunker (token-aware, max CHUNK_MAX_TOKENS).
Tables are not taken from Docling: its tables mirror the HTML layout grid, so every
table is replaced by one "table_row" chunk per row of the clean table from
ingest/sec_tables.py (title + units + header + that row), which keeps each figure next
to the labels needed to read it.
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
from docling_core.transforms.serializer.markdown import MarkdownTableSerializer
from docling_core.types.doc import DoclingDocument

from ingest.sec_tables import ExtractedTable, extract_sec_tables

CHUNK_MAX_TOKENS = 512
DOWNLOADS_DIR = Path(__file__).resolve().parents[2] / "data" / "downloads"
MANIFEST_PATH = DOWNLOADS_DIR / "manifest.json"

ITEM_SECTION_RE = re.compile(r"\bItem\s+[\dA-Z.]+\b", re.IGNORECASE)


@dataclass(frozen=True)
class ChunkRecord:
    chunk_index: int
    text: str
    page: str | None
    section: str | None
    token_count: int
    chunk_metadata: dict[str, Any]


class PatchedOpenAITokenizer(OpenAITokenizer):
    """Counts tokens without rejecting text that happens to contain tiktoken special tokens."""

    def count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text, allowed_special=set(), disallowed_special=()))


class MarkdownTableSerializerProvider(ChunkingSerializerProvider):
    """Serialize tables as Markdown (Docling's default is "row, column = value" triplets).

    Markdown lines start with "|", which is how table content is recognised and stripped
    from narrative chunks below.
    """

    def get_serializer(self, doc: DoclingDocument) -> ChunkingDocSerializer:
        return ChunkingDocSerializer(doc=doc, table_serializer=MarkdownTableSerializer())


def build_hybrid_chunker(max_tokens: int = CHUNK_MAX_TOKENS) -> HybridChunker:
    tokenizer = PatchedOpenAITokenizer(tokenizer=tiktoken.get_encoding("cl100k_base"), max_tokens=max_tokens)
    return HybridChunker(
        tokenizer=tokenizer,
        merge_peers=True,
        repeat_table_header=True,
        serializer_provider=MarkdownTableSerializerProvider(),
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


def page_from_chunk_meta(meta: Any) -> str | None:
    # SEC HTML has no pages, so this is normally None; kept for sources that do (e.g. PDF).
    for item in meta.doc_items or []:
        for provenance in item.prov or []:
            if provenance.page_no is not None:
                return str(provenance.page_no)
    return None


def section_from_chunk(meta: Any, text: str) -> str | None:
    if meta.headings:
        return " > ".join(meta.headings)
    match = ITEM_SECTION_RE.search(text)
    return match.group(0) if match else None


def narrative_text_without_tables(text: str) -> str:
    return "\n".join(line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("|"))


def _chunk_contains_table(chunk: Any) -> bool:
    return any("table" in item.label.value for item in chunk.meta.doc_items or [])


def _table_matches_chunk(chunk_text: str, table: ExtractedTable) -> bool:
    rows = table.table_data["rows"]
    if not rows:
        return False
    first_row = rows[0]
    if first_row["label"] and first_row["label"] in chunk_text:
        return True
    return any(value.strip("$") in chunk_text for value in first_row["values"] if value)


def _matching_table(chunk_text: str, tables: list[ExtractedTable], used: set[int]) -> ExtractedTable | None:
    return next(
        (table for table in tables if table.table_index not in used and _table_matches_chunk(chunk_text, table)),
        None,
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
    chunker = build_hybrid_chunker()
    count_tokens = chunker.tokenizer.count_tokens
    base = base_chunk_metadata(filing)
    records: list[ChunkRecord] = []
    used_tables: set[int] = set()

    def add_narrative(text: str, meta: Any) -> None:
        records.append(
            ChunkRecord(
                chunk_index=len(records),
                text=text,
                page=page_from_chunk_meta(meta),
                section=section_from_chunk(meta, text),
                token_count=count_tokens(text),
                chunk_metadata={**base, "chunk_kind": "narrative", "docling_meta": meta.export_json_dict()},
            )
        )

    def add_table_rows(table: ExtractedTable) -> None:
        for row in table.table_data["rows"]:
            text = table_row_chunk_text(table, row)
            records.append(
                ChunkRecord(
                    chunk_index=len(records),
                    text=text,
                    page=None,
                    section=table.title,
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

    document = convert_html_to_document(html_path)
    for index, chunk in enumerate(chunker.chunk(dl_doc=document)):
        if max_chunks is not None and index >= max_chunks:
            break
        text = chunker.contextualize(chunk=chunk)
        if not _chunk_contains_table(chunk):
            add_narrative(text, chunk.meta)
            continue

        table = _matching_table(text, tables, used_tables)
        if table is None:
            # A layout table (prose, footnotes, cover page) that sec_tables skipped: keep it as is.
            add_narrative(text, chunk.meta)
            continue
        narrative = narrative_text_without_tables(text)
        if narrative:
            add_narrative(narrative, chunk.meta)
        add_table_rows(table)

    # Tables no Docling chunk matched still belong in the index.
    if max_chunks is None:
        for table in tables:
            if table.table_index not in used_tables:
                add_table_rows(table)
    return records
