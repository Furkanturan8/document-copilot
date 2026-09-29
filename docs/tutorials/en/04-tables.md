# Chapter 4 — Tables: The Hardest Part of RAG

> **In this chapter:** why financial tables need special handling in RAG, the table grid inside SEC HTML, and how we rebuilt a clean table from that grid step by step. At the end: how we verified the extraction and the bugs we found.

## 4.1 A number alone says nothing

Take the number `201,183`. What does it mean? You need three more things:

- **Row label:** `iPhone`
- **Column header:** `2024`
- **Unit:** `in millions` (millions of dollars)

Together they mean: "Apple's iPhone net sales in fiscal 2024 were $201,183 million". If a RAG system separates these four pieces, the language model either reads the wrong column or cannot use the number at all. Since the most critical information for financial questions is in tables, extracting tables correctly is perhaps the biggest single factor in retrieval quality.

## 4.2 The hidden grid of SEC tables

SEC filings use a very fine grid to align tables visually. The raw HTML of the "iPhone" row in Apple's table (styles removed):

```html
<tr>
  <td colspan="3"><span>iPhone</span></td>
  <td><span>$</span></td>
  <td><span>201,183&#160;</span></td>
  <td/><td colspan="3"/>
  <td colspan="2"><span>&#8212;&#160;</span></td>
  <td><span>%</span></td>
  ...
</tr>
```

Things to notice:

- **`colspan`:** a cell spans several columns (`iPhone` spans 3).
- **Split values:** `$` in one cell, `201,183` in the next; `—` in one cell, `%` in another.
- **Empty spacer cells:** spacing columns made of `<td/>`.
- **`&#160;`:** invisible space characters.

Docling copies this grid into Markdown as is. Because it writes a merged cell once per column, a row of 6 values spreads over ~30 columns (Chapter 3). Our target instead:

```text
|  | 2024 | Change | 2023 | Change | 2022 |
|---|---|---|---|---|---|
| iPhone | $201,183 | —% | $200,583 | (2)% | $205,489 |
| Mac | 29,984 | 2% | 29,357 | (27)% | 40,177 |
```

## 4.3 The approach: rebuild the table from the raw HTML

Following the reference project, we rebuilt tables with our own code from the **raw HTML**, not from Docling's Markdown (`backend/ingest/sec_tables.py`), using only Python's standard library (`html.parser`). The algorithm is like solving a puzzle piece by piece. The steps:

### Step 1 — HTML into a tree

`HTMLParser` builds a tree with every tag as a node (`_Node`). Nodes with `style="display:none"` (hidden XBRL) are skipped. Walking the document gives an ordered list of blocks: text blocks and table blocks. A table's title will be found in the text blocks right before it.

One subtlety when joining text: inline tags are joined **without spaces** (`B<span>USINESS</span>` → `BUSINESS`); block tags (`div`, `p`) get a space between them.

### Step 2 — Give every cell a position on the grid

For each cell we compute its **start** and **end** column on the grid. A `colspan="3"` cell spans 0 to 3. Two traps:

- **`rowspan`:** a cell reaching down from the row above fills those columns in the row below. Ignore it and the lower row's cells shift one column left. In Apple's debt table the "Maturities" heading spanned two rows; the first version missed this and every header shifted by one column.
- **Empty cells:** their positions count but their content is dropped.

Each row becomes a list of `(start, end, text)` tokens.

### Step 3 — Merge the fragments

Pieces that belong together become one value:

| Raw pieces | Merged value | Rule |
|---|---|---|
| `$` · `201,183` | `$201,183` | `$` and `(` attach to the next value |
| `(7)` · `%` | `(7)%` | `%` and `)` attach to the previous value |
| `0.48%` · `–` · `0.63%` | `0.48% – 0.63%` | A short dash between two values of the same kind (two percentages, two years) is a range |
| `$1,200` · `—` · `$900` | stay separate | A **long dash** (`—`) means "zero/none" in SEC filings; it is a value of its own |

The last two rows matter: the short dash (`–`) and the long dash (`—`) mean different things. Treating them the same would either split ranges or glue "zero" values to their neighbors.

### Step 4 — Recognize data rows

A row that starts with a **label** followed by at least one **number** is a data row: `iPhone | $201,183 | ...`. One trap: `(In millions) | 2024 | 2023` also looks like label + numbers, but the numbers are years. So **rows containing only years count as headers**. Without this rule about half of Microsoft's tables lost their header.

"Number" is defined broadly: `201,183`, `$1.5`, `(2)`, `(7)%`, ranges such as `0.1%-1.6%`, and `—`.

### Step 5 — Find the logical columns

The grid has 30 columns but the table has 6 logical ones. To find them we collect the grid ranges of all values in the data rows and **merge overlapping ranges into the same column** (interval clustering):

```text
$201,183 → 3-5     29,984 → 3-5     → Column 1: 3-5
—%       → 9-12    2%     → 9-12    → Column 2: 9-12
...
```

Text cells count too. "Up 53%" in NVIDIA's summary table is not a number but has its own column; looking only at numbers would glue it to the neighboring column.

### Step 6 — Place the headers

The rows before the first data row split in two:

- **Header rows:** rows reaching into the value columns (`2024 | Change | 2023`). Each header is placed in the column it **overlaps**. A group header spanning several columns (`Year Ended January 31, 2021`) is added to each column it covers: `Year Ended January 31, 2021 (…)`.
- **Section rows:** rows that stay in the label column only (`Operating expenses:`). These are sub-headings inside the table, not headers. The first version mixed them into the header.

### Step 7 — Drop tables that are not tables

Some "tables" are only layout; we skip them:

- Tables with a cell longer than 200 characters: bulleted text, footnotes, auditor notes.
- Tables whose first rows mention "Exhibit": exhibit lists.
- Tables without a real financial value: tables of contents with only small page numbers.

The **text in these tables is not lost**: it is in Docling's output and enters chunks as plain text (Chapter 5).

### Step 8 — Find the title and unit

A table's topic is usually in the sentence right above it: *"The following table shows net sales by category for 2024, 2023 and 2022 (dollars in millions):"*. But other things can sit right above a table too, so we look back over the last 4 text blocks and **skip**:

- Page footers (`35`, `Apple Inc. | 2024 Form 10-K | 35`)
- Page headers (`Table of Contents`)
- Unit lines (`(In millions)`); they feed the unit instead
- `(Continued)`
- Bare section labels (`Item 8`, `PART II`)
- Company name headers (`MICROSOFT CORPORATION`)

A table that follows another with no text in between inherits the previous table's title; it is usually the continuation of the same topic. The unit (`in millions, except per share data`) is searched in the title, nearby text and the column headers.

This rule did not exist at first: ~10% of tables had meaningless titles such as `35` or `(In millions)`. After the fix, Apple's financial statements got their real names, such as `CONSOLIDATED BALANCE SHEETS`.

### Step 9 — The output

For each table:

```python
ExtractedTable(
    table_index=5,                     # position in the document
    title="The following table shows net sales by category ...",
    units="in millions",
    markdown="|  | 2024 | Change | ... |",   # clean Markdown
    table_data={"columns": [...], "rows": [{"label": "iPhone", "values": [...]}]},
    source_html_hash="…",               # digest of the raw content (to notice changes)
)
```

`table_data` is the machine-readable table. It can later be used to show the table in the UI or highlight a row.

## 4.4 Verifying the extraction: is every number there?

"The tables look fine" is not enough. We wrote a **coverage check**: is every number of every financial table in the HTML present in the extracted tables?

The first measurement found a bug in the check itself: joining cells without spaces put `2023` and `1,560` together as `20231,560`, which looked like a fake "loss". The measuring tool needs verifying too. With the corrected check, we fixed the bug found in each round and measured again:

| Round | State |
|---|---|
| First version | ~40 Microsoft tables without headers, Apple columns merged |
| Year-header rule | Microsoft headers came back |
| Range rule | Apple interest-rate columns separated |
| Single-cell ranges | Skipped NVIDIA and Microsoft tables found |
| `rowspan` | Header shift in Apple's debt table fixed |
| Text columns | NVIDIA's "Up 53%" column separated |
| Layout-table filter | Exhibit lists and plain-text tables left out |
| Title rule | No more meaningless titles (footers, unit lines) |

Final state: **1,407 tables** from 25 filings, and **no lost numbers** in financial tables. The few remaining "losses" come from cover pages and exhibit lists left out on purpose.

## 4.5 Examples from the result

Shortened examples from the five companies' 2025 income statements:

```text
Microsoft — SUMMARY RESULTS OF OPERATIONS
| (In millions, except percentages and per share amounts) | 2025 | 2024 | Percentage Change |
| Revenue | $281,724 | $245,122 | 15% |

NVIDIA — Fiscal Year 2025 Summary
|  | Year Ended Jan 26, 2025 (...) | Year Ended Jan 28, 2024 (...) | Year Ended Change (...) |
| Revenue | $130,497 | $60,922 | Up 114% |

Apple — (In millions, except …)
|  | Years ended September 27, 2025 | Years ended September 28, 2024 | … |
| Net sales: |  |  |  |
| Products | $307,003 | $294,866 | $298,085 |
```

## 4.6 The `document_tables` table

Clean tables live in their own database table: `document_id`, `table_index`, `title`, `units`, `markdown`, `table_data` and `source_html_hash`. Chunks link to these tables through `table_id` (Chapter 5).

## Summary

- A financial number means something only with its row label, column header and unit; RAG must keep them together.
- SEC tables sit on a fine grid; the table must be rebuilt from cell positions (colspan/rowspan).
- The algorithm: positions → fragment merging → data rows → column clustering → headers → layout filter → title/unit.
- Every rule answers a real bug found by measuring; without the coverage check most of them would have gone unnoticed.

## Sources

- Code: `backend/ingest/sec_tables.py`, tests: `backend/tests/ingest/test_sec_tables.py`
- Python `html.parser`: <https://docs.python.org/3/library/html.parser.html>

---
[← Turning documents into text](03-document-to-text.md) · Next chapter: [Chunking →](05-chunking.md)
