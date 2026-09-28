"""Register the converted filings in source_documents.

This is the source stage only: filing metadata from data/downloads/manifest.json and the
Docling Markdown from data/markdown/ (run data/convert_to_markdown.py first). Everything
derived from a filing (tables, chunks, embeddings) is written by the chunking stage, per
document and in one transaction, so those artifacts are always replaced together and
never point at each other across different extraction runs. No paid APIs are called.

Run from backend/:

    uv run python -m ingest.load_source_documents
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database.models import SourceDocument

# Params: edit these, then rerun.
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DOWNLOADS_DIR = DATA_DIR / "downloads"
MARKDOWN_DIR = DATA_DIR / "markdown"
# False re-writes the metadata and Markdown of documents that already exist.
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
    engine = create_engine(settings.sqlalchemy_database_url)
    counts = {"inserted": 0, "updated": 0, "skipped": 0}

    with Session(engine) as session:
        # Only ids are fetched: a full row carries up to ~1 MB of Markdown per filing.
        rows = session.execute(select(SourceDocument.accession_number, SourceDocument.id))
        existing_ids = {accession_number: document_id for accession_number, document_id in rows}

        for filing in manifest["filings"]:
            accession_number = filing["accession_number"]
            if accession_number in existing_ids and SKIP_EXISTING:
                counts["skipped"] += 1
                continue

            markdown_path = (MARKDOWN_DIR / filing["local_path"]).with_suffix(".md")
            if not markdown_path.is_file():
                raise FileNotFoundError(f"{markdown_path} is missing; run data/convert_to_markdown.py first.")
            fields = document_fields(filing, markdown_path.read_text(encoding="utf-8"))

            if accession_number in existing_ids:
                document = session.get_one(SourceDocument, existing_ids[accession_number])
                for key, value in fields.items():
                    setattr(document, key, value)
                counts["updated"] += 1
            else:
                session.add(SourceDocument(**fields))
                counts["inserted"] += 1
            # One commit per filing, so an interrupted run keeps what it finished.
            session.commit()
            print(f"{filing['ticker']:5} FY{fields['fiscal_year']} {accession_number}", flush=True)

    print(f"Done: {counts['inserted']} inserted, {counts['updated']} updated, {counts['skipped']} skipped.")


if __name__ == "__main__":
    main()
