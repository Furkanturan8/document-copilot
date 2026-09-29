# Chapter 5 — Chunking: Splitting Documents into Pieces

> **In this chapter:** why we split documents into pieces (chunks), why chunk size matters, what a "token" is, Docling's chunker, and the ideas we added: replacing tables in place with clean rows, removing noise, and finding every chunk's **page** and **section**.

## 5.1 Why split?

Every library book has an index at the back: "Inflation — pp. 45, 112". The index does not say "in this book"; it says **on which page**. Chunking splits documents into small pieces such an index can point to. There are three reasons:

1. **Search precision.** As the next chapter shows, each piece is represented by a single vector (embedding). Compress a 100-page report into one vector and its meaning blurs into "a bit of everything". A small piece's vector clearly reflects that piece's topic.
2. **Give the model only what it needs.** We give the language model 10 short relevant passages, not 100 pages. That is cheaper and does not scatter its attention.
3. **Citation precision.** The answer cites "Apple 2024 10-K, p. 23, Item 7", not just "Apple 2024 10-K". The smaller the piece, the more precise the citation.

## 5.2 How big? A trade-off

| If chunks are small | If chunks are large |
|---|---|
| ✅ Clear meaning, precise citation | ✅ Rich context; sentences stay whole |
| ❌ Cut off from context ("This increase…" which increase?) | ❌ Blurred meaning, lower search precision |
| ❌ Many pieces, more storage | ❌ Unneeded text goes to the model, higher cost |

A common fix is "overlap": consecutive chunks repeat part of each other, so a sentence at the boundary is in both. Following the reference we took another route: no overlap, but search also returns each hit's **previous and next chunk (its neighbors)** (Chapter 9). Context arrives when it is needed.

We use a chunk size of **512 tokens** (`CHUNK_MAX_TOKENS`).

## 5.3 What is a token?

Language models do not process text letter by letter or word by word, but in pieces called **tokens**. A token is usually a word or part of a word: `"revenue"` is one token, `"unconsolidated"` may be several. In English, 1 token ≈ 4 characters ≈ ¾ of a word on average. 512 tokens is roughly 350–400 words, or 1.5–2 paragraphs.

Why count tokens and not characters? Because the limits and prices of both the embedding model and the language model are in tokens. To measure chunks correctly you must use **the same tokenizer** as the model. OpenAI's embedding model uses the `cl100k_base` encoding, and we count chunks in that encoding with the `tiktoken` library.

A small trap: if the text contains a sequence that tiktoken treats as "special", such as `<|endoftext|>`, the default settings raise an error. That is why the reference has a `PatchedOpenAITokenizer`: it counts those sequences as ordinary text.

## 5.4 Docling's chunkers

Docling offers two chunkers ([documentation](https://docling-project.github.io/docling/concepts/chunking/)):

- **HierarchicalChunker:** splits by the document's structure; each document item (paragraph, table, list) becomes a chunk, with metadata such as headings attached.
- **HybridChunker:** adds token awareness on top. It makes two passes: (1) split chunks above the token limit, (2) merge small consecutive chunks that share a heading (`merge_peers=True`).

`chunker.contextualize(chunk)` returns a chunk's text, enriched with heading information where available. SEC HTML has no heading tags, so this enrichment stays empty for us; we find the heading ourselves (5.8).

## 5.5 Two kinds of chunks

Our system has two kinds of chunks (`metadata.chunk_kind`):

**1. `narrative`: plain text.** Comes from HybridChunker. Example:

```text
Services net sales increased during 2024 compared to 2023 due primarily to higher net
sales from advertising, the App Store and cloud services.
```

**2. `table_row`: a table row.** **Every row** of a clean table (Chapter 4) becomes its own chunk and carries everything needed to read that row:

```text
The following table shows net sales by category for 2024, 2023 and 2022 (dollars in millions):
Units: in millions
|  | 2024 | Change | 2023 | Change | 2022 |
|---|---|---|---|---|---|
| iPhone | $201,183 | —% | $200,583 | (2)% | $205,489 |
```

Why row by row? A search for "iPhone 2024 revenue" finds exactly the iPhone row instead of the whole table. Because the chunk also carries the title, unit and column names, the language model reads the number correctly. The full table stays in `document_tables`; the `table_id` in each row chunk's metadata points to it.

## 5.6 Replacing tables in place: the placeholder method

There is a problem: HybridChunker also writes Docling's **own** tables (with the broken grid) into the text. How do we replace them with clean table rows, without losing the table's place in the document?

The answer is to give Docling **our own table serializer**:

1. **Matching:** before chunking, each Docling table is matched to one of the clean tables by comparing their numbers: if at least 80% of the clean table's numbers are in the Docling table, they are the same table. Both lists are in document order, so matching walks forward.
2. **Placeholder:** the matched table is written into the chunk text as a small marker such as `[[table:5]]`.
3. **Replacement:** when processing chunks, on seeing a marker we make the text before it a `narrative` chunk, add that table's row chunks, then continue with the rest of the text.

Result: tables stay in their place in the document, the broken grid never enters the index, and a large table split over several chunks is not indexed twice.

Tables that match nothing are layout tables: bulleted text, footnotes, Amazon's section headings. We turn them into **plain text** without repeated cells, so their content is not lost.

> **A difference from the reference.** The reference project removed lines starting with `|` from chunks that contain tables and matched only a table's first piece to the clean table. The continuation pieces of large tables could not be matched and entered the index with their broken grid; in Apple 2024, ~60% of text chunks were like that. We changed the method after seeing that measurement.

### The "visited" mark

The "rich cells" from Chapter 3 showed up here: Docling also stores the content of table cells as separate text items under the table. Docling's own table serializer marks these child items `visited` when it writes the table, so the chunker does not write them a second time. Our serializer did not, and labels such as `iPhone (1)` and `Mac (1)` entered the index again as text chunks. Adding the marking removed 524 duplicate chunks.

**Lesson:** when you replace part of a library with your own code, you also take over the "invisible" duties the original part performed.

## 5.7 Removing noise

Every chunk's text goes through this cleanup (`clean_chunk_text`):

- **Page footers** are removed (`Apple Inc. | 2024 Form 10-K | 35`).
- **Repeated page headers** are removed (`Table of Contents`).
- **Markdown links** are reduced to their text: `[Note 11 - Debt](#i7bfb_94)` → `Note 11 - Debt`. Anchor codes and URLs are meaningless noise for search.

## 5.8 Every chunk's page and section

A citation is worth only as much as the reader's ability to find it in the original. "Apple 2024 10-K, p. 23, Item 7" is something an analyst can go and check. But as Chapter 2 showed, HTML has neither pages nor heading tags. We derived this information ourselves.

The core idea: **the evidence is rarely inside a single chunk, but it is in the document as a whole.** So page and section are computed before chunking, over the whole document, item by item (`document_positions`).

### Page: "a footer closes its page"

In a printed report the page number is at the **end** of the page. When a footer appears in the document flow, the content before it was on that page. So an item's page is **the number of the first footer after it**:

```text
... "Services net sales increased ..."     → page 23 (next footer is 23)
... "Mac net sales ..."                    → page 23
"Apple Inc. | 2024 Form 10-K | 23"          ← footer
... "Gross margin ..."                     → page 24
"Apple Inc. | 2024 Form 10-K | 24"          ← footer
```

Walking the document from the end carries "the next footer" easily. Recognized footer formats: `35`, `35.` and `Apple Inc. | 2024 Form 10-K | 35`.

But not every lone number in the text is a footer. Two safety rules:

1. **Numbers must increase:** an accepted footer must be larger than the previous one, by at most 3. A stray "7" in the middle of the text is dropped.
2. **Listings are dropped:** a table of contents or an "Index to Financial Statements" lists page numbers such as `49`, `51`, `52` one after another. Real footers have a page of content between them; listing numbers come a few items apart. Runs of 3 or more increasing candidates at most 3 items apart are not footers (`_dense_runs`). Without this rule a Google chunk got an impossible page range of "49-58".

A chunk crossing a page break gets a range such as `"23-24"`.

### Section: the last "Item" heading

Each item's section is the last `Item N.` heading before it. Heading rules:

- The line must start with `Item` and be short (at most 200 characters), so sentences such as "as described in Item 7, …" are not taken for headings.
- Lines ending in a page number (`Item 1A. Risk Factors 13`) are table-of-contents lines, not headings.
- Tables of contents come in other forms too (at NVIDIA, `Item 1.` / `Business` / `4` on separate lines). So the "dense run" rule applies here as well: runs of 5 or more headings at most 3 items apart and in **increasing order** (1, 1A, 1B, 2…) are a table of contents. The real `Item 1.` heading does not join the run, because the order drops from 16 back to 1.

As the section name we use **the SEC's standard title**, not the company's wording: `Item 7. Management's Discussion and Analysis of Financial Condition and Results of Operations`. That way Microsoft's split headings such as `ITEM 1. B USINESS` are recognized too, and every company gets consistent section names.

## 5.9 Metadata: the chunk's ID card

Each chunk carries an ID card next to its text:

| Field | Example | Used for |
|---|---|---|
| `chunk_index` | 312 | Order in the document; finding neighbors |
| `page` | `"23-24"` | Citation |
| `section` | `Item 7. Management's …` | Citation, context |
| `token_count` | 187 | Cost and limit checks |
| `metadata.ticker`, `fiscal_year`, `form`, `accession_number`, `source_url` | `AAPL`, 2024, … | Filtering and citation |
| `metadata.chunk_kind` | `table_row` | Chunk kind |
| `metadata.table_id`, `table_title`, `row_label` | … | Link to the table, for row chunks |

Metadata is critical for two things: **filters** during search (Chapters 7, 9) and **citations** in answers (Chapter 12).

## 5.10 Result

For 25 filings:

| | Reference logic | Our result |
|---|---|---|
| Total chunks | 19,409 | **16,498** (no duplicates) |
| Text chunks containing Docling's grid | ~60% at Apple | **0** |
| Page filled | 0% | **99.4%** |
| Section filled | ~13% | **98.6%** (the rest is the cover page) |
| Tokens embedded | ~4.3 million | **~2.4 million** |

About 12,300 chunks are table rows and about 4,200 are narrative text.

## Summary

- Chunking sharpens search, gives the model only what it needs and makes citations precise.
- Chunk size is a trade-off; we use 512 tokens and provide context through neighboring chunks.
- Tokens are the model's unit of text; count them with the model's own tokenizer.
- Tables are chunked row by row, with title and unit; Docling's tables are replaced in place through placeholders.
- Page and section are found by looking at the whole document: a footer closes its page, the last Item heading sets the section, and table-of-contents and index listings are dropped.

## Sources

- Docling chunking concepts: <https://docling-project.github.io/docling/concepts/chunking/>
- OpenAI tiktoken: <https://github.com/openai/tiktoken>
- Code: `backend/ingest/chunking.py`, tests: `backend/tests/ingest/test_chunking.py`

---
[← Tables](04-tables.md) · Next chapter: [Embeddings →](06-embeddings.md)
