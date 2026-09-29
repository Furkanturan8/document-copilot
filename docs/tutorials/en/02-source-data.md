# Chapter 2 — Source Data: SEC 10-K Reports

> **In this chapter:** we get to know what we search. What is a 10-K, what do the files look like, and why are they not "just a text file"? We also learn the **source data / derived data** split that the whole ingestion pipeline rests on.

## 2.1 The first rule of RAG: know your data

A search system is only as good as your understanding of the documents it searches. Which information sits where, in what format, and where are the traps? The answers drive every later design decision, so look at the data before writing code.

## 2.2 What is a 10-K?

Public companies in the US must file a detailed annual report called a **10-K** with the regulator, the **SEC** (Securities and Exchange Commission). The reports are published in the open **EDGAR** system and anyone can download them.

A 10-K's structure is set by law and consists of standard sections called **Items**:

| Item | Topic | Why it matters to an analyst |
|---|---|---|
| Item 1 | Business | What the company does, products, customers |
| Item 1A | Risk Factors | Risks: export controls, supply chain, regulation |
| Item 7 | Management's Discussion and Analysis (MD&A) | Management's commentary on results: revenue, margins, trends |
| Item 7A | Quantitative and Qualitative Disclosures About Market Risk | Currency and interest-rate risks |
| Item 8 | Financial Statements | Income statement, balance sheet, cash flows and notes |
| Item 15 | Exhibits | Attachments; some companies put the financial statements here |

This standard structure helps a lot. Knowing which Item a passage is in tells us much about the answer's nature: risk language, management commentary or audited figures? That is why Chapter 5 extracts each chunk's section.

### The fiscal-year trap

A company's fiscal year does not have to match the calendar year:

- Apple's fiscal year ends in late September (FY2024 = the year ended September 28, 2024).
- Microsoft's ends in late June.
- NVIDIA's ends in late January, so **NVIDIA FY2025** is the year that ended in **January 2025**.

So we derive `fiscal_year` from the **end date of the period the report covers** (`report_date`, in `backend/ingest/load_source_documents.py`). Finding the right document for "the 2025 report" depends on it for every company.

## 2.3 Downloading the data

`data/download.py` downloads the last five years of 10-Ks for five companies (AAPL, MSFT, NVDA, AMZN, GOOGL) from EDGAR into per-year folders and writes `data/downloads/manifest.json`, with one record per file:

```json
{
  "ticker": "AAPL",
  "cik": "0000320193",
  "form": "10-K",
  "filing_date": "2024-11-01",
  "report_date": "2024-09-28",
  "accession_number": "0000320193-24-000123",
  "source_url": "https://www.sec.gov/Archives/edgar/data/320193/...",
  "local_path": "2024/aapl_10-k_2024-11-01_0000320193-24-000123.htm"
}
```

- **CIK:** the permanent ID the SEC gives a company.
- **Accession number:** the unique number of each filing. We use it to identify a document uniquely in the database.

## 2.4 What the files look like inside

10-Ks are HTML files in "inline XBRL" format. In a browser you see a clean report; in the source, things get messy. The features we met, and solved in later chapters:

1. **Hidden machine-readable data.** A block hidden with `display:none` at the top holds XBRL: accounting data tagged for computers. It is not on screen and must not enter our text, because it is not what an analyst reads.
2. **No heading tags.** The `Item 7. Management's Discussion…` heading is not an `<h1>` or `<h2>` but an ordinary `<div>` styled bold, so "find the headings automatically" does not work (Chapter 5).
3. **Tables used for layout.** HTML tables are used not only for financial data but also to align bulleted lists, footnotes, the table of contents and even section headings (Chapter 4).
4. **Financial tables on a fine grid.** A single value is split over several cells: `$` in one cell, the number in the next, `%` in another (Chapter 4).
5. **No "pages" in HTML.** The printed report has page numbers, but the HTML is one long flow. Page numbers survive only as footers inside the text: `Apple Inc. | 2024 Form 10-K | 35` for Apple, a bare `35` for Microsoft (Chapter 5).
6. **Split words.** Microsoft's headings contain words split across tags, such as `B<span>USINESS</span>`.

The quality of a RAG system is often decided not by the model's intelligence but by how well such "boring" details are handled.

## 2.5 Source data and derived data

The most important design idea of the ingestion pipeline is separating two kinds of data:

- **Source data:** the document itself and its metadata: the downloaded HTML, its Markdown, the company, year and accession number. It does not change unless the document does.
- **Derived data:** everything **produced** from the source data by an algorithm: clean tables, chunks and embeddings. It must be regenerated when the algorithm changes (for example, when a table-extraction rule is fixed).

Why does this matter? Derived data is interlinked: a table-row chunk points to its table through `table_id`. Produce the tables at one time and the chunks at another, and a chunk may point to a table left over from an older run that no longer exists or is wrong. That is a wrong citation, directly.

Therefore:

- The **source stage** (`backend/ingest/load_source_documents.py`) only registers documents in `source_documents`.
- The **derivation stage** (`backend/ingest/chunk_and_embed.py`) deletes and rewrites each document's tables, chunks and embeddings **together, in one database transaction**.

Chapter 10 returns to this.

## 2.6 The `source_documents` table

Each 10-K is one row in the database. The important columns:

| Column | Description |
|---|---|
| `ticker`, `cik`, `company_name` | The company |
| `filing_type` | `10-K` |
| `filing_date`, `report_date`, `fiscal_year` | Time information |
| `accession_number` | Unique ID |
| `source_url` | The original document on EDGAR, to go from a citation to the original |
| `content_markdown` | The Markdown produced by Docling (Chapter 3) |
| `ingested_at` | Set once tables, chunks and embeddings are written |

A small performance note: `content_markdown` can reach 1 MB per document. The model marks it `deferred=True`, so it loads only when asked for. We did this because the "does this document already exist?" check downloaded megabytes every time; the check dropped from 43 to 7 seconds.

## Summary

- A 10-K is a public annual report with a standard structure (Items); that structure lets us tag passages with a section.
- The files are HTML with traps: hidden data, headings made with styling, tables used for layout, and no concept of pages.
- Separating source data from derived data, and writing derived data together, is what keeps citations consistent.

## Sources

- SEC EDGAR: <https://www.sec.gov/edgar/search/>
- Code: `data/download.py`, `backend/ingest/load_source_documents.py`, `backend/app/database/models/source_document.py`

---
[← What is RAG?](01-what-is-rag.md) · Next chapter: [Turning documents into text →](03-document-to-text.md)
