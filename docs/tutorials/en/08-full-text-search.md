# Chapter 8 — Full-Text Search

> **In this chapter:** why "classic" search that catches words exactly is still needed, Postgres's full-text tools (`tsvector`, `tsquery`, the GIN index, `ts_rank_cd`), and how we turn a question into search terms. We also see the "AND trap" we found by measuring.

## 8.1 Catching what embeddings miss

Chapter 6 showed that embeddings capture meaning but are weak on exact terms. An analyst asking about "AWS operating income" wants passages that contain **exactly "AWS"**; general passages about "cloud services revenue" are not enough. The same holds for product names (`iPhone`, `Azure`, `Blackwell`), section codes (`Item 1A`), form names (`10-K`) and technical terms (`export controls`).

Word-based (lexical) search exists for these cases. The **index** at the back of a book is a good analogy: "AWS — pp. 23, 45, 67". It knows nothing about meaning, but finds every place a word occurs, exactly.

## 8.2 Postgres's full-text tools

### `tsvector`: the text's "index form"

`to_tsvector('english', text)` turns a text into a searchable form:

```text
to_tsvector('english', 'Services net sales increased due to higher App Store sales')

→ 'app':8 'due':5 'higher':7 'increas':4 'net':2 'sale':3,10 'servic':1 'store':9
```

(This is real output from our database. The word `to` is in position 6 but missing from the list because it is a stop word.)

What happened:

- **Lower-casing:** `Services` → `servic…`
- **Stemming:** `Services` → `servic`, `increased` → `increas`, `sales` → `sale`. "sale" and "sales" reduce to the same stem and match the same search. (Irregular forms such as "sold" are not caught by stemming.)
- **Dropping stop words:** words without meaning such as `to` and `the` do not enter the index.
- **Positions:** `sale` occurs at positions 3 and 10; ranking uses positions to see how close words are.

The result of this process is called a **lexeme**.

### Generated column: a column that updates itself

`document_chunks.search_vector` is not filled by hand. We tell Postgres "always compute this column from `content`":

```sql
search_vector tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED
```

When a chunk's text changes (during link cleanup, for example), `search_vector` updates automatically.

### GIN index: an inverted index

Scanning the `tsvector` of 16,500 rows one by one on every search would be slow. **GIN** (Generalized Inverted Index) is the book index itself: for each lexeme it keeps the list of rows it occurs in. Asked for `'aws'`, it goes straight to that list.

### `tsquery` and `@@`: query and match

On the search side, text becomes a `tsquery` and matches with the `@@` operator:

```sql
SELECT * FROM document_chunks
WHERE search_vector @@ plainto_tsquery('english', 'iPhone net sales');
-- plainto_tsquery → 'iphon' & 'net' & 'sale'
```

`plainto_tsquery` normalizes the query text the same way (stems, lower case, stop words) and joins the words with **`&` (AND)**.

### Ranking: `ts_rank_cd`

Which matching passage is more relevant? `ts_rank_cd` ("cover density") looks at how often the query terms occur in the passage and **how close together** they are. A passage where "iPhone net sales" appear side by side scores higher than one where the three words are scattered across the page.

> **A note on BM25.** The cookbook's hybrid search example uses **BM25**, a classic ranking formula that gives rare words more weight (IDF) and accounts for document length. Postgres's built-in `ts_rank` and `ts_rank_cd` do not use IDF; they are similar to BM25 but not the same. At our scale they work well enough, and having them in the same database as vector search is a big practical advantage.

## 8.3 The AND trap: zero results

The first version followed the reference and used `plainto_tsquery`, so terms were joined with AND. In the smoke test we measured the keywords of the 10 questions:

| Keywords | Matching with AND | Containing at least one |
|---|---|---|
| `revenue mix iPhone Services Mac` | **0** | 347 |
| `AI infrastructure Capital expenditures purchase` | **0** | 527 |
| `Revenue geographic area latest filing` | **0** | 670 |
| `cloud capacity AI infrastructure Azure` | 2 | 387 |
| `customer concentration Data Center demand` | 5 | 815 |

For 3 of the 10 questions full-text search returned **nothing**, and for 3 more fewer than 5 results. A passage containing **all five** terms at once is very rare.

### The fix: search with OR, put the best-covered first

We keep `plainto_tsquery`'s normalization but replace the `&` signs with `|` (OR). Passages are then ranked by two criteria:

1. **How many distinct terms does it contain?** A passage with 4 terms comes before one with 1.
2. On a tie, **`ts_rank_cd`**.

```sql
WITH q AS (
    SELECT CAST(replace(CAST(plainto_tsquery(cfg, :query_text) AS text), '&', '|') AS tsquery) AS query,
           tsvector_to_array(to_tsvector(cfg, :query_text)) AS terms
)
SELECT dc.id,
       (SELECT count(*) FROM unnest(q.terms) AS term
        WHERE dc.search_vector @@ CAST(quote_literal(term) AS tsquery)) AS matched_terms,
       ts_rank_cd(dc.search_vector, q.query) AS score
FROM document_chunks dc JOIN source_documents sd ON ..., q
WHERE dc.search_vector @@ q.query
ORDER BY matched_terms DESC, score DESC
LIMIT :limit
```

We also tried ranking by `ts_rank_cd` alone. Passages that contained one frequent word such as "Services" many times came first: for the geographic revenue question, the Graphics segment ranked first. With "matched terms first", NVIDIA's "Revenue by geographic areas" note came first.

Result: **all** 10 questions have 50 candidates.

## 8.4 Turning a question into keywords

Giving the user's question straight to full-text search does not work well: "How did NVIDIA describe demand drivers, customer concentration, and supply constraints for its Data Center business?" contains words such as "how", "did", "describe" and "its" that distinguish nothing. So `backend/app/retrieval/keywords.py` reduces the question to 3–5 distinctive terms:

1. **Short queries are used as is:** a query of 5 words or fewer already looks like keywords (`iPhone net sales`).
2. **A small LLM picks the terms:** `gpt-4.1-mini` returns 3–5 terms through structured output (`KeywordExtraction`, a Pydantic model). The prompt has rules: skip filler words, prefer standard SEC phrases ("data center", "customer concentration"), keep product names as written.
3. **Proper names the user typed come first:** capitalized names in the question (`Azure`, `iPhone`) and known phrases (`data center`) go to the front of the term list.
4. **The company name is dropped:** when the search is already filtered by ticker, "NVIDIA" distinguishes nothing.
5. **A word budget:** at most 5 words in total.
6. **A rule-based fallback:** if the LLM call fails, the same rules are applied without the model. Full-text search gets somewhat weaker, but semantic search is unaffected and the system keeps working.

Example outputs:

| Question | Keywords |
|---|---|
| NVIDIA's demand, customer concentration and supply constraints | `customer concentration Data Center demand` |
| Microsoft's Azure, AI infrastructure and cloud capacity | `cloud capacity AI infrastructure Azure` |
| Apple's revenue mix | `revenue mix iPhone Services Mac` |

## Summary

- Full-text search catches the exact terms, codes and product names where embeddings are weak.
- Postgres turns text into a `tsvector` (lexemes: stemmed, lower-cased, stop words removed); the GIN index works like a book index.
- `plainto_tsquery` joins terms with AND, which gave zero results for multi-term queries. We fixed it with OR plus a "matched terms" ranking.
- Questions are reduced to 3–5 keywords by an LLM step that keeps proper names and tolerates failure.

## Sources

- PostgreSQL full-text search: <https://www.postgresql.org/docs/current/textsearch.html>
- Ranking functions (`ts_rank`, `ts_rank_cd`): <https://www.postgresql.org/docs/current/textsearch-controls.html>
- Cookbook, BM25 explained: <https://github.com/daveebbelaar/ai-cookbook/tree/main/knowledge/hybrid-retrieval/docs>
- Code: `backend/app/retrieval/queries.py`, `backend/app/retrieval/keywords.py`

---
[← Vector search](07-vector-search.md) · Next chapter: [Hybrid search and RRF →](09-hybrid-search-and-rrf.md)
