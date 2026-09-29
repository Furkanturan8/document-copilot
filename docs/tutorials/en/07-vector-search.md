# Chapter 7 — Vector Search: pgvector and HNSW

> **In this chapter:** how we quickly find the vectors "nearest" to a question's vector among thousands or millions, what pgvector adds to Postgres, the intuition behind the HNSW index, and the trap we hit with filtered searches, where results silently disappear.

## 7.1 The problem: finding the nearest neighbors

We have 16,498 chunk vectors. When a question arrives we turn it into a vector too (Chapter 6) and ask: **which 50 vectors are nearest to this one?** This is called nearest neighbor search.

There are two ways:

- **Exact search (brute force):** compare the question vector with each of the 16,498 vectors, sort, take the top 50. Always correct, but very slow once there are millions of vectors.
- **Approximate search (ANN, approximate nearest neighbor):** use a clever index structure to look at a tiny share of the vectors and find the "almost certainly" nearest ones. Very fast, at the price of a very small loss in accuracy.

## 7.2 pgvector: vector abilities for Postgres

A separate "vector database" (Pinecone, Weaviate, LanceDB…) is a common choice for storing vectors. Following the reference architecture we use **Postgres with the pgvector extension**. The advantages:

- **One database:** chunk text, metadata, vectors, chats and users live in one place, with no separate system to keep in sync.
- **The power of SQL:** vector search combines with `JOIN` and `WHERE` ("only NVIDIA's 2025 report").
- **Transactions:** tables, chunks and vectors are written consistently in one transaction (Chapter 10).

What pgvector adds:

- **The `vector(n)` type:** the `embedding vector(1536)` column.
- **Distance operators:** `<->` (L2/Euclidean), `<#>` (negative inner product), `<=>` (cosine distance), `<+>` (L1). We use the cosine, the standard for text embeddings, so `<=>`.
- **Index types:** HNSW and IVFFlat. We use HNSW.

The simplest form:

```sql
SELECT id, 1 - (embedding <=> :question_vector) AS similarity
FROM document_chunks
ORDER BY embedding <=> :question_vector
LIMIT 50;
```

## 7.3 The intuition behind HNSW: a city with express roads

HNSW (Hierarchical Navigable Small World) organizes vectors as a **multi-layer graph**. It is like finding your way in a city:

- **Top layer:** motorways connecting only a few big junctions.
- **Middle layers:** main streets.
- **Bottom layer:** every street; every vector is here.

The search starts at the top layer: take the motorway to the junction that gets you closest to the target, drop a layer and keep approaching on main streets, and finally collect the neighbors around the target at street level. Because each layer follows only links that "get closer", a tiny share of the vectors is visited.

Important settings in pgvector (with defaults):

| Setting | Default | Meaning |
|---|---|---|
| `m` | 16 | Maximum links per node per layer |
| `ef_construction` | 64 | Size of the candidate list considered while building the index |
| `hnsw.ef_search` | **40** | Size of the candidate list kept during search |

`ef_search` is the hero of this chapter: a search collects at most that many candidates. Larger means more accurate but slower; smaller means faster but less accurate.

The index is in the model definition and the migration:

```python
Index("ix_document_chunks_embedding_hnsw", "embedding",
      postgresql_using="hnsw", postgresql_ops={"embedding": "vector_cosine_ops"})
```

`vector_cosine_ops` says the index is built for cosine distance; the query must use `<=>`, or the index is not used.

## 7.4 The trap: filters silently destroy results

When the user asks about "Microsoft's capex", we restrict the search to Microsoft:

```sql
... WHERE sd.ticker = 'MSFT' ORDER BY embedding <=> :v LIMIT 50
```

In the smoke test this query returned **3** results, not 50. The pgvector documentation states the reason plainly: with approximate indexes the filter is applied **after the index scan**. HNSW finds 40 candidates by default, then the `ticker = 'MSFT'` filter is applied to those 40. If only 3 of the 40 come from Microsoft, the result is 3. The documentation's example: a condition matching 10% of rows returns only 4 rows on average.

Even more interesting: **unfiltered** searches asking for 50 returned 40, because `ef_search` capped the candidates at 40 and 50 were never collected. The reference project has the same issue.

This is one of the sneakiest failure modes in RAG: **no error message, just missing results.** The user only sees the model say "I could not find enough evidence", while the evidence sits in the database.

### The fix: iterative index scan

pgvector 0.8 added **iterative index scans**, which keep scanning the index until enough results pass the filter. There are two modes:

- `strict_order`: results exactly ordered by distance.
- `relaxed_order`: results may come slightly out of order, but recall (the share of right results found) is better.

There is a safety limit too: `hnsw.max_scan_tuples` (default 20,000) caps the rows scanned.

Our query (`backend/app/retrieval/queries.py`):

```sql
-- Settings for this transaction only (same effect as SET LOCAL):
SELECT set_config('hnsw.iterative_scan', 'relaxed_order', true),
       set_config('hnsw.ef_search', '50', true);

WITH candidates AS MATERIALIZED (
    SELECT dc.id, dc.embedding <=> CAST(:query_vec AS vector) AS distance
    FROM document_chunks dc
    JOIN source_documents sd ON sd.id = dc.document_id
    WHERE dc.embedding IS NOT NULL AND sd.ticker = :ticker
    ORDER BY distance
    LIMIT :limit
)
SELECT id, 1 - distance AS score FROM candidates ORDER BY distance + 0;
```

Three tricks here:

1. **`set_config(..., true)`:** `true` makes the setting valid for this transaction only, so other queries in the connection pool are not affected. Sending both settings in one `SELECT` saves a network round trip (~360 ms).
2. **`MATERIALIZED` CTE:** the candidates are collected in a separate step first.
3. **`ORDER BY distance + 0`:** `relaxed_order` can return results slightly out of order, so we re-sort outside. But with a plain `ORDER BY distance`, Postgres thought "these are already sorted" and skipped the sort; verification showed the order was wrong. `+ 0` forces Postgres to really re-sort, which is also what the pgvector documentation recommends.

Result: filtered or not, every search returns 50 candidates, correctly ordered.

## 7.5 Not carrying large columns

The search returns only `id` and distance; the text is fetched later in a separate step (Chapter 9). In the ORM models the `embedding` (~20 KB), `search_vector` and `content_markdown` (~1 MB) columns are `deferred=True`, so reading a row loads these large columns only when asked for. With a remote database, what data crosses the network directly decides performance.

## Summary

- Vector search finds the vectors nearest to the question's vector; at scale, approximate (ANN) indexes do this.
- pgvector brings vector search into Postgres, usable with SQL filters and transactions.
- HNSW searches by "getting closer" on a layered graph; `ef_search` sets the number of candidates.
- With approximate indexes the filter is applied afterwards, which can silently shrink the results. The fix is an iterative scan plus a real re-sort.

## Sources

- pgvector documentation (HNSW, filtering, iterative index scans): <https://github.com/pgvector/pgvector>
- The HNSW paper, Malkov and Yashunin: <https://arxiv.org/abs/1603.09320>
- Code: `backend/app/retrieval/queries.py`, `backend/app/database/models/document_chunk.py`

---
[← Embeddings](06-embeddings.md) · Next chapter: [Full-text search →](08-full-text-search.md)
