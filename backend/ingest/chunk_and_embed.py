"""Chunking stage: derive tables, chunks and embeddings from registered filings.

Per document, everything derived from it is written in ONE transaction: document_tables,
then document_chunks (whose metadata points at their table via table_id), then
source_documents.ingested_at. A rerun with --force deletes and rewrites that set together,
so chunks never reference tables from a different extraction run.

Run from backend/ after ingest.load_source_documents:

    uv run python -m ingest.chunk_and_embed --all --dry-run   # chunk only: no OpenAI calls, no writes
    uv run python -m ingest.chunk_and_embed --all             # embeds with OpenAI (paid) and writes
    uv run python -m ingest.chunk_and_embed --accession 0000320193-24-000123 --force
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime

from sqlalchemy import create_engine, delete, exists, select
from sqlalchemy.orm import Session, defer

from app.config import settings
from app.database.models import (
    DocumentChunk,
    DocumentTable,
    MessageCitation,
    SourceDocument,
)
from ingest.chunking import (
    CHUNK_MAX_TOKENS,
    ChunkRecord,
    chunk_document,
    html_path_for_accession,
)
from ingest.embeddings import EMBED_BATCH_SIZE, embed_texts


def filing_metadata(document: SourceDocument) -> dict:
    return {
        "ticker": document.ticker,
        "cik": document.cik,
        "company_name": document.company_name,
        "form": document.filing_type,
        "filing_date": document.filing_date.isoformat(),
        "report_date": document.report_date.isoformat(),
        "fiscal_year": document.fiscal_year,
        "accession_number": document.accession_number,
        "primary_document": document.primary_document,
        "source_url": document.source_url,
    }


def document_has_chunks(session: Session, document: SourceDocument) -> bool:
    return bool(session.scalar(select(exists().where(DocumentChunk.document_id == document.id))))


def delete_derived(session: Session, document: SourceDocument) -> None:
    # Citations reference chunks with ON DELETE RESTRICT, so they have to go first.
    chunk_ids = select(DocumentChunk.id).where(DocumentChunk.document_id == document.id)
    session.execute(delete(MessageCitation).where(MessageCitation.chunk_id.in_(chunk_ids)))
    session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
    session.execute(delete(DocumentTable).where(DocumentTable.document_id == document.id))
    document.ingested_at = None


def tables_from_records(document: SourceDocument, records: list[ChunkRecord]) -> list[DocumentTable]:
    tables: dict[int, DocumentTable] = {}
    for record in records:
        table = record.chunk_metadata.get("table")
        if record.chunk_metadata["chunk_kind"] != "table_row" or table["table_index"] in tables:
            continue
        tables[table["table_index"]] = DocumentTable(
            document_id=document.id,
            table_index=table["table_index"],
            title=table["title"],
            units=table["units"],
            markdown=table["markdown"],
            table_data=table["table_data"],
            source_html_hash=table["source_html_hash"],
        )
    return list(tables.values())


def ingest_document(
    session: Session,
    document: SourceDocument,
    *,
    max_chunks: int | None = None,
    dry_run: bool = False,
    force: bool = False,
) -> int | None:
    """Chunk, embed and store one filing. Returns the number of chunks, or None if skipped."""
    if not force and document_has_chunks(session, document):
        print(f"{document.accession_number}: already chunked, skipping (use --force to redo)")
        return None

    records = chunk_document(
        html_path_for_accession(document.accession_number), filing_metadata(document), max_chunks=max_chunks
    )
    kinds = {kind: sum(1 for r in records if r.chunk_metadata["chunk_kind"] == kind) for kind in ("narrative", "table_row")}
    print(
        f"{document.ticker} FY{document.fiscal_year} {document.accession_number}: {len(records)} chunks {kinds}, "
        f"max {max(r.token_count for r in records)}/{CHUNK_MAX_TOKENS} tokens"
    )
    if dry_run:
        return len(records)

    vectors = embed_texts([record.text for record in records])

    # Reached only with --force or when the document has no chunks; either way any tables
    # still stored are from an earlier run and must not survive next to the new chunks.
    delete_derived(session, document)
    tables = tables_from_records(document, records)
    session.add_all(tables)
    session.flush()  # assigns table ids for the chunk metadata below
    table_ids = {table.table_index: str(table.id) for table in tables}

    for record, vector in zip(records, vectors, strict=True):
        metadata = dict(record.chunk_metadata)
        if metadata["chunk_kind"] == "table_row":
            metadata["table_id"] = table_ids[metadata["table_index"]]
        session.add(
            DocumentChunk(
                document_id=document.id,
                chunk_index=record.chunk_index,
                section=record.section,
                page=record.page,
                content=record.text,
                token_count=record.token_count,
                embedding=vector,
                metadata_=metadata,
            )
        )
    document.ingested_at = datetime.now(UTC)
    session.commit()
    print(f"  wrote {len(tables)} tables and {len(records)} chunks (embedding batch size {EMBED_BATCH_SIZE})")
    return len(records)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--all", action="store_true", help="process every registered filing")
    target.add_argument("--accession", help="process one filing by accession number")
    parser.add_argument("--dry-run", action="store_true", help="chunk only; no OpenAI calls, no database writes")
    parser.add_argument("--force", action="store_true", help="delete and rewrite existing chunks and tables")
    parser.add_argument("--max-chunks", type=int, help="stop after this many Docling chunks (for quick tests)")
    args = parser.parse_args()

    engine = create_engine(settings.sqlalchemy_database_url)
    processed = skipped = chunks = 0
    with Session(engine) as session:
        query = select(SourceDocument).order_by(SourceDocument.ticker, SourceDocument.fiscal_year)
        if args.accession:
            query = query.where(SourceDocument.accession_number == args.accession)
        # content_markdown is not needed here and is up to ~1 MB per filing.
        documents = session.scalars(query.options(defer(SourceDocument.content_markdown))).all()
        for document in documents:
            written = ingest_document(
                session, document, max_chunks=args.max_chunks, dry_run=args.dry_run, force=args.force
            )
            if written is None:
                skipped += 1
            else:
                processed += 1
                chunks += written

    action = "chunked (dry run, nothing written)" if args.dry_run else "written"
    print(f"Done: {processed} documents processed, {skipped} skipped, {chunks} chunks {action}.")


if __name__ == "__main__":
    main()
