# Chapter 3 — Turning Documents into Text (Parsing)

> **In this chapter:** how to turn a complex document such as HTML into text that search and language models can use (parsing), how Docling represents a document, and how we verified a conversion's quality by **measuring** it.

## 3.1 Why "parsing"?

A language model or a search engine can do nothing with tags like `<td style="padding:2px 1pt">`. What they need is the document's **content** and **structure**: paragraphs, headings, lists, tables. Parsing turns a document in a raw format (HTML, PDF, DOCX…) into that structured content.

A good parser must preserve three things:

1. **All the text:** no paragraph or number may be lost.
2. **Reading order:** text must come in the order a person reads it.
3. **Structure:** what is a heading, a table or a list must be known.

## 3.2 Docling

[Docling](https://docling-project.github.io/docling/) is an open-source document conversion library developed by IBM. It reads PDF, DOCX, PPTX, HTML and many other formats into a common model (`DoclingDocument`) and exports that as Markdown, JSON or HTML.

### DoclingDocument: a document as a tree

Docling keeps a document not as flat text but as a **tree of items**:

- **`TextItem`:** a paragraph, heading or list item.
- **`TableItem`:** a table, with its cells, row and column positions and merged-cell (span) information.
- **`GroupItem`:** a node that groups items (a list, for example).
- **`PictureItem`:** an image.

`doc.iterate_items()` walks this tree in document order. Chapter 5 finds page and section information exactly by walking it.

> **An interesting detail: "rich cells".** Docling also stores the content of formatted table cells (for example `iPhone (1)` with a footnote superscript) as **separate `TextItem`s under the table**. In Apple's 2021 report, 423 of 1,097 text items were of this kind. We did not notice at first, so table labels entered the index a second time as "plain text" for a while. Chapter 5 explains the fix.

## 3.3 The conversion script

`data/convert_to_markdown.py` saves `data/downloads/<year>/*.htm` as `data/markdown/<year>/*.md`, keeping the folder structure. Its core:

```python
converter = DocumentConverter(allowed_formats=[InputFormat.HTML])
for result in converter.convert_all(pending, raises_on_error=False):
    if result.status not in (ConversionStatus.SUCCESS, ConversionStatus.PARTIAL_SUCCESS):
        ...  # report the failed file and continue
    result.document.save_as_markdown(temp)
    temp.replace(target)
```

Three small ideas worth learning:

1. **`allowed_formats=[InputFormat.HTML]`:** telling Docling we only process HTML means the heavy AI models for PDF/OCR are never loaded.
2. **`raises_on_error=False`:** an error in one file does not stop the run; errors are reported at the end.
3. **Write to a temporary file, then rename (atomic write):** if the script is interrupted, no half-written `.md` is left on disk. Because the script skips already converted files, a half-written file would otherwise count as "done" on the next run.

Converting 25 files took 86 seconds.

## 3.4 Measuring conversion quality

Instead of "converted, done", we asked: **does the Markdown really carry all the information in the HTML?** We wrote a comparison script for 6 files covering all five companies and four different years:

1. Parse the HTML, drop hidden (`display:none`) sections and get the visible text.
2. **Number check:** extract every number from the visible text (`201,183`, `0.48`…) and check it appears in the Markdown.
3. **Table check:** check that every HTML table's numbers are found in the Markdown.
4. **Word check:** check that words of five or more letters in the HTML appear in the Markdown.
5. **Leak check:** look for words in the Markdown that are not in the visible HTML, to see whether hidden XBRL data leaked.

Result:

| Check | Result |
|---|---|
| Lost numbers | None (the one apparently missing number came from the file name) |
| Lost words | None |
| Hidden XBRL leak | None |
| Extra "words" | Link targets: `(#i7bfb…)` anchors and EDGAR URLs |

**No data loss.** But four structural problems appeared that later steps had to solve.

## 3.5 The problems found

### Problem 1: broken tables

Apple's "net sales by category" table looked like this in Markdown (shortened):

```text
|        |        |        | 2024   |    2024 | 2024 |    |    |    | Change | Change | Change | ...
| iPhone | iPhone | iPhone | $      | 201,183 |      |    |    |    | -      | -      | %      | ...
| Mac    | Mac    | Mac    | 29,984 |  29,984 |      |    |    |    | 2      | 2      | %      | ...
```

A row with 6 values spreads over about **30 columns**. The values are right, but it is very hard for a language model to answer "which column is 2023 iPhone revenue?" reliably. That is the next chapter's topic.

### Problem 2: tables used for layout

Apple has empty tables, Amazon writes section headings as table rows (`| Item 1A. | Risk Factors |`), and Google repeats a "Table of Contents | Alphabet Inc." row on every page.

### Problem 3: links

In-page links such as `[Table of Contents](#i7bfbfbe5…)` and exhibit URLs are mixed into the text: noise for search.

### Problem 4: inconsistent page and section markers

- Page footers: `Apple Inc. | 2024 Form 10-K | 35` at Apple, `35` at Microsoft, Amazon and NVIDIA, `35.` at Google.
- Section headings: `ITEM 1. B USINESS` at Microsoft (letters split), inside a table at Amazon.

## 3.6 The decision

Following the reference project:

- **`content_markdown` stores Docling's output as is**, as the document's "readable full version".
- **Tables are extracted separately and cleanly from the raw HTML** and stored in `document_tables` (Chapter 4).
- **Noise cleanup, page and section information are handled at chunking** (Chapter 5).

## Summary

- Parsing makes a raw document usable as content and structure.
- Docling keeps a document as a tree of items (`DoclingDocument`); walking that tree is how structural information is reached.
- Conversion quality is not assumed but measured: number, word and leak checks showed there is no data loss.
- No data is lost, but tables, layout tables, links and page/section markers need extra work.

## Sources

- Docling documentation: <https://docling-project.github.io/docling/>
- End-to-end example with Docling (extraction, chunking, embedding, search): <https://github.com/daveebbelaar/ai-cookbook/tree/main/knowledge/docling>
- Code: `data/convert_to_markdown.py`

---
[← Source data](02-source-data.md) · Next chapter: [Tables →](04-tables.md)
