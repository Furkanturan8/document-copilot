# Data

Local data artifacts for development live here.

- `downloads/` holds raw source files fetched from SEC EDGAR, grouped by year.
- `markdown/` holds the Docling Markdown export of each filing, in the same year layout.
- Downloaded and converted files are gitignored because the corpus can get large.
- Fetch a sample corpus with `uv run data/download.py`
- Convert it to Markdown with `cd backend && uv run python ../data/convert_to_markdown.py` (Docling is a backend dev dependency). Already converted filings are skipped; set `OVERWRITE = True` in the script to redo them.
