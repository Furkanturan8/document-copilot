"""Convert downloaded SEC filings (downloads/<year>/*.htm) to Markdown with Docling.

Output mirrors the input layout: downloads/2024/x.htm -> markdown/2024/x.md.

Docling is a backend dev dependency, so run this with the backend environment:

    cd backend && uv run python ../data/convert_to_markdown.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from docling.datamodel.base_models import ConversionStatus, InputFormat
from docling.document_converter import DocumentConverter

# Params: edit these, then rerun.
DATA_DIR = Path(__file__).resolve().parent
INPUT_DIR = DATA_DIR / "downloads"
OUTPUT_DIR = DATA_DIR / "markdown"
# False skips filings whose .md already exists, so an interrupted run can simply be restarted.
OVERWRITE = False


def output_path(source: Path) -> Path:
    return OUTPUT_DIR / source.relative_to(INPUT_DIR).with_suffix(".md")


def main() -> int:
    sources = sorted(INPUT_DIR.glob("*/*.htm"))
    if not sources:
        print(f"No .htm files under {INPUT_DIR}. Run `uv run data/download.py` first.")
        return 1

    pending = [source for source in sources if OVERWRITE or not output_path(source).exists()]
    print(f"{len(sources)} filings found, {len(sources) - len(pending)} already converted, {len(pending)} to convert.")
    if not pending:
        return 0

    # HTML only: keeps Docling on its HTML backend and away from the PDF/OCR model pipeline.
    converter = DocumentConverter(allowed_formats=[InputFormat.HTML])
    failed: list[Path] = []
    started = time.monotonic()

    results = converter.convert_all(pending, raises_on_error=False)
    for index, result in enumerate(results, start=1):
        source = Path(result.input.file)
        label = f"[{index}/{len(pending)}] {source.relative_to(INPUT_DIR)}"

        if result.status not in (ConversionStatus.SUCCESS, ConversionStatus.PARTIAL_SUCCESS):
            failed.append(source)
            print(f"{label}: FAILED ({result.status.name}) {[error.error_message for error in result.errors]}")
            continue

        target = output_path(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        # Written to a temp file first so a crash never leaves a truncated .md that a rerun would skip.
        temp = target.with_suffix(".md.tmp")
        result.document.save_as_markdown(temp)
        temp.replace(target)

        note = f" with {len(result.errors)} warning(s)" if result.status == ConversionStatus.PARTIAL_SUCCESS else ""
        print(f"{label}: ok{note} -> {target.relative_to(DATA_DIR)} ({target.stat().st_size / 1_000_000:.1f} MB)")

    print(f"Done in {time.monotonic() - started:.0f}s: {len(pending) - len(failed)} converted, {len(failed)} failed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
