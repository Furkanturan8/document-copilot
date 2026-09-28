from datetime import date

from ingest.load_source_documents import document_fields

NVDA_FILING = {
    "ticker": "NVDA",
    "cik": "0001045810",
    "form": "10-K",
    "filing_date": "2025-02-26",
    "report_date": "2025-01-26",
    "accession_number": "0001045810-25-000023",
    "primary_document": "nvda-20250126.htm",
    "source_url": "https://www.sec.gov/Archives/edgar/data/1045810/000104581025000023/nvda-20250126.htm",
    "local_path": "2025/nvda_10-k_2025-02-26_0001045810-25-000023.htm",
}


def test_document_fields_map_manifest_metadata():
    fields = document_fields(NVDA_FILING, "# markdown")

    assert fields["company_name"] == "NVIDIA Corporation"
    assert fields["filing_type"] == "10-K"
    assert fields["filing_date"] == date(2025, 2, 26)
    # NVIDIA's fiscal 2025 ends in January 2025, so the fiscal year follows the report date.
    assert fields["fiscal_year"] == 2025
    assert fields["content_markdown"] == "# markdown"
    assert "ingested_at" not in fields
