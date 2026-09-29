# Chapter 6 — Embeddings: Turning Meaning into Numbers

> **In this chapter:** what an embedding is, how "close in meaning" becomes "close in numbers", how similarity is measured, and how the project uses OpenAI's embedding model.

## 6.1 Searching by words is not enough

An analyst asks: "How did Apple's phone revenue change?" The report says: *"iPhone net sales increased during 2024 …"*. The two sentences share almost no words: "iPhone" instead of "phone", "net sales" instead of "revenue". Classic keyword search misses the match, while a person sees immediately that both talk about the same thing.

Embeddings are how a computer gets this "same meaning" intuition.

## 6.2 A map analogy

Think of a city map. Every place has coordinates: (latitude, longitude). Places near each other have nearby coordinates, and you can compute the distance between two cafés from their coordinates.

An embedding model draws **a map for texts**. It gives every text coordinates, but in a space with **1536 dimensions**, not 2. On this map:

- "iPhone net sales increased" and "phone revenue went up" are **near** each other.
- "iPhone net sales increased" and "the company is subject to export controls" are **far** apart.

That list of coordinates (an array of 1536 numbers) is called a **vector** or an **embedding**:

```text
"iPhone net sales increased"  →  [0.0123, -0.0441, 0.0078, …, 0.0215]   (1536 numbers)
```

No single dimension carries a meaning on its own (there is no "dimension 37 = revenue"). Meaning lies in the position the numbers form together. The model learned this map by training on huge amounts of text: expressions used in similar contexts end up in nearby positions.

## 6.3 Measuring similarity: cosine similarity

The way to measure how much two vectors "point the same way" is **cosine similarity**. The intuition: two arrows pointing the same way have similarity 1, perpendicular arrows 0, opposite arrows −1.

A small 2-dimensional example:

```text
A = [0.8, 0.6]   ("iPhone sales")
B = [0.7, 0.7]   ("phone revenue")
C = [-0.6, 0.8]  ("export restrictions")

similarity(A, B) = (0.8·0.7 + 0.6·0.7) / (|A|·|B|) = 0.98 / (1 · 0.99) ≈ 0.99   → very similar
similarity(A, C) = (0.8·(−0.6) + 0.6·0.8) / (|A|·|C|) = 0.00 → unrelated
```

Databases usually work with **distance** instead of similarity: `cosine distance = 1 − cosine similarity`. The smaller the distance, the more similar the texts. In pgvector this is the `<=>` operator (Chapter 7).

## 6.4 The model we use

**OpenAI `text-embedding-3-small`**, producing 1536-dimensional vectors. The choice comes from the reference project, for these reasons:

- A good balance of quality and price: about $0.02 per million tokens. Our whole corpus (~2.4 million tokens) was embedded for about $0.05.
- 1536 dimensions match the database's `vector(1536)` column. The model can produce shorter vectors through the `dimensions` parameter, but it must match the column.

### The golden rule: same model, same dimensions

Whatever model you embedded the documents with, embed the questions with **the same model and the same dimensions**. Different models draw different maps; looking up one map's coordinates on another's is meaningless. That is why the model name and dimensions live in one place, `app/config.py`, and ingestion and search use the same setting.

## 6.5 Embedding the chunks

`backend/ingest/embeddings.py`:

```python
for start in range(0, len(texts), batch_size):          # groups of 100
    response = client.embeddings.create(
        input=texts[start : start + batch_size],
        model=settings.openai_embedding_model,
        dimensions=settings.openai_embedding_dimensions,
    )
    for item in sorted(response.data, key=lambda item: item.index):
        if len(item.embedding) != dimensions:
            raise ValueError(...)
        vectors.append(item.embedding)
```

Three small but important details:

1. **Batching:** instead of one request per text, 100 texts go in one request, far more efficient for network round trips and rate limits.
2. **Sorting by `index`:** to be sure every vector matches the right text, we sort by the `index` field the API returns. If the order got mixed up, one text's vector would be written to another text, and that would be almost impossible to notice.
3. **Dimension check:** a vector of unexpected size raises an error immediately; stopping is better than writing wrong data to the database.

Queries do the same with a single text (`backend/app/retrieval/embeddings.py` → `embed_query`).

## 6.6 The limits of embeddings

Embeddings are powerful but do not catch everything:

- **Exact words and codes:** terms such as "AWS", "Item 1A", "10-K" or "1099-MISC" have no near-synonyms; what matters is the exact match. Embeddings can be weak here.
- **Numbers:** "201,183" and "200,583" can be close in embedding space but are completely different facts.
- **Negation:** "Revenue increased" and "revenue did not increase" can land surprisingly close.

So we combine embedding search with **full-text search**, which catches words exactly (Chapters 8 and 9). The cookbook's measurements show this too: on a financial question-answering dataset (FiQA), keyword search alone (BM25) scores NDCG@10 ≈ 0.24, embeddings alone ≈ 0.31, and the combination ≈ 0.35.

## 6.7 Storage cost: a small surprise

A vector of 1536 numbers looks small, but:

- Sent to the database as text (`[0.0123,-0.0441,…]`), it takes **~19 KB** per chunk.
- 16,500 chunks × 19 KB ≈ **300 MB** of data.

Our upload speed to Supabase was ~40 KB/s, so uploading the whole corpus took **more than 2 hours**. OpenAI produced the embeddings in seconds; the bottleneck was entirely the network. In real projects it is a good habit to measure such "invisible" costs in advance (Chapter 10).

## Summary

- An embedding turns text into a vector (a "coordinate on a map") that reflects its meaning; texts close in meaning get close vectors.
- Similarity is measured with the cosine; databases work with the distance `1 − similarity`.
- Documents and questions must be embedded with the same model and dimensions.
- Batching, sorting by `index` and a dimension check are the three basic safeguards of a reliable embedding pipeline.
- Embeddings are weak on exact words and numbers, which is why we combine them with full-text search.

## Sources

- OpenAI embeddings guide: <https://platform.openai.com/docs/guides/embeddings>
- Cookbook, dense search with embeddings: <https://github.com/daveebbelaar/ai-cookbook/tree/main/knowledge/hybrid-retrieval/docs>
- Code: `backend/ingest/embeddings.py`, `backend/app/retrieval/embeddings.py`

---
[← Chunking](05-chunking.md) · Next chapter: [Vector search →](07-vector-search.md)
