"""Load the converted filings into source_documents, plus their tables into document_tables.

Reads data/downloads/manifest.json for filing metadata, the Docling Markdown from
data/markdown/ (run data/convert_to_markdown.py first), and re-extracts tables from the
raw HTML (see ingest/sec_tables.py). No paid APIs are called.

Run from backend/:

    uv run python -m ingest.load_source_documents
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database.models import DocumentTable, SourceDocument
from ingest.sec_tables import extract_sec_tables

# Params: edit these, then rerun.
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DOWNLOADS_DIR = DATA_DIR / "downloads"
MARKDOWN_DIR = DATA_DIR / "markdown"
# False re-writes existing documents and replaces their tables.
SKIP_EXISTING = True

COMPANY_NAMES = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "NVDA": "NVIDIA Corporation",
    "AMZN": "Amazon.com, Inc.",
    "GOOGL": "Alphabet Inc.",
}


def document_fields(filing: dict, markdown: str) -> dict:
    report_date = date.fromisoformat(filing["report_date"])
    return {
        "ticker": filing["ticker"],
        "cik": filing["cik"],
        "company_name": COMPANY_NAMES.get(filing["ticker"]),
        "filing_type": filing["form"],
        "filing_date": date.fromisoformat(filing["filing_date"]),
        "report_date": report_date,
        # The fiscal year is named after the year it ends in (NVIDIA's FY2025 ends January 2025).
        "fiscal_year": report_date.year,
        "accession_number": filing["accession_number"],
        "primary_document": filing["primary_document"],
        "source_url": filing["source_url"],
        "content_markdown": markdown,
    }


def main() -> None:
    manifest = json.loads((DOWNLOADS_DIR / "manifest.json").read_text(encoding="utf-8"))
    filings = manifest["filings"]
    engine = create_engine(settings.sqlalchemy_database_url)
    counts = {"inserted": 0, "updated": 0, "skipped": 0, "tables": 0}

    with Session(engine) as session:
        for filing in filings:
            accession_number = filing["accession_number"]
            existing = session.scalar(select(SourceDocument).where(SourceDocument.accession_number == accession_number))
            if existing and SKIP_EXISTING:
                counts["skipped"] += 1
                continue

            html_path = DOWNLOADS_DIR / filing["local_path"]
            markdown_path = (MARKDOWN_DIR / filing["local_path"]).with_suffix(".md")
            if not markdown_path.is_file():
                raise FileNotFoundError(f"{markdown_path} is missing; run data/convert_to_markdown.py first.")

            fields = document_fields(filing, markdown_path.read_text(encoding="utf-8"))
            if existing:
                for key, value in fields.items():
                    setattr(existing, key, value)
                document = existing
                session.execute(delete(DocumentTable).where(DocumentTable.document_id == document.id))
                counts["updated"] += 1
            else:
                document = SourceDocument(**fields)
                session.add(document)
                session.flush()
                counts["inserted"] += 1

            tables = extract_sec_tables(html_path.read_text(encoding="utf-8", errors="replace"))
            session.add_all(
                DocumentTable(
                    document_id=document.id,
                    table_index=table.table_index,
                    title=table.title,
                    units=table.units,
                    markdown=table.markdown,
                    table_data=table.table_data,
                    source_html_hash=table.source_html_hash,
                )
                for table in tables
            )
            # One commit per filing, so an interrupted run keeps what it finished.
            session.commit()
            counts["tables"] += len(tables)
            print(f"{filing['ticker']:5} FY{fields['fiscal_year']} {accession_number}: {len(tables)} tables")

    print(
        f"Done: {counts['inserted']} inserted, {counts['updated']} updated, "
        f"{counts['skipped']} skipped, {counts['tables']} tables written."
    )


if __name__ == "__main__":
    main()
