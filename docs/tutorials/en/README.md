# Learning RAG from Scratch, with Document Copilot

This folder explains the **RAG (Retrieval-Augmented Generation)** architecture built in the Document Copilot project, as a book, for someone who has never met the topic. Each chapter first explains a concept with an everyday analogy, then shows how our code applies it, which decisions we made and why, and the results we measured.

The chapters are meant to be read in order; each builds on the previous one. A Turkish version is in [`../tr/`](../tr/README.md).

## Contents

| # | Chapter | What you will learn |
|---|---|---|
| 1 | [What is RAG?](01-what-is-rag.md) | Why language models are not enough alone, how RAG solves that, the big picture |
| 2 | [Source data: SEC 10-K reports](02-source-data.md) | What we search, what the documents look like, "source data" vs "derived data" |
| 3 | [Turning documents into text (parsing)](03-document-to-text.md) | HTML to Markdown with Docling, measuring conversion quality |
| 4 | [Tables: the hardest part of RAG](04-tables.md) | Rebuilding financial tables cleanly from raw HTML |
| 5 | [Chunking: splitting documents into pieces](05-chunking.md) | Why we split, how big, how page and section are found |
| 6 | [Embeddings: turning meaning into numbers](06-embeddings.md) | Vectors, similarity, the OpenAI embedding model |
| 7 | [Vector search: pgvector and HNSW](07-vector-search.md) | Finding the nearest among millions of vectors fast, the filter trap |
| 8 | [Full-text search](08-full-text-search.md) | Catching words exactly, Postgres `tsvector`, keyword extraction |
| 9 | [Hybrid search and RRF](09-hybrid-search-and-rrf.md) | Combining two searches, Reciprocal Rank Fusion, the whole retriever |
| 10 | [Ingestion pipeline and database](10-ingestion-and-database.md) | From document to database end to end, the full schema, performance lessons |
| 11 | [Measuring quality](11-measuring-quality.md) | Telling "looks like it works" from "works", the bugs we found, budgeted benchmarks |
| 12 | [Answer generation and grounding](12-answer-generation-and-grounding.md) | The agent and its tools, the typed answer, the deterministic validator, numeric checks, the anatomy of cost, measurements, blind spots |
| 13 | [Jev: typed decisions, a risk signal and question routing](13-jev-typed-decisions.md) | A decision model that produces no text: the risk signal, question routing, advantages and limits |
| — | [Glossary](glossary.md) | Short explanations of the terms used in the book |

## Code map

The book often refers to file paths. In short:

```text
data/
├── download.py                  # Download 10-Ks from SEC EDGAR         (Chapter 2)
└── convert_to_markdown.py       # HTML → Markdown with Docling          (Chapter 3)
backend/
├── ingest/
│   ├── load_source_documents.py # Register source documents             (Chapters 2, 10)
│   ├── sec_tables.py            # Clean table extraction from raw HTML   (Chapter 4)
│   ├── chunking.py              # Chunks, page, section                  (Chapter 5)
│   ├── embeddings.py            # Chunk embeddings                       (Chapter 6)
│   └── chunk_and_embed.py       # Writing the derived data               (Chapter 10)
└── app/retrieval/
    ├── embeddings.py            # Query embedding                        (Chapter 6)
    ├── queries.py               # Vector and full-text SQL               (Chapters 7, 8)
    ├── keywords.py              # Keywords for full-text search          (Chapter 8)
    ├── fusion.py                # RRF                                    (Chapter 9)
    ├── retriever.py             # The orchestrator combining it all      (Chapter 9)
    └── types.py                 # Filters, passages, agent formatting    (Chapter 9)
backend/app/
├── assistant/
│   ├── agent.py                 # PydanticAI agent and safety limits     (Chapter 12)
│   ├── tools.py                 # search_filings, read_chunks …          (Chapter 12)
│   ├── instructions.md          # The product contract (instructions)    (Chapter 12)
│   └── router.py                # Question routing with Jev              (Chapter 13)
├── grounding/
│   ├── validator.py             # Deterministic citation checks          (Chapter 12)
│   ├── numeric.py               # Figures checked in code                (Chapter 12)
│   ├── claims.py                # Answer → claims                        (Chapter 13)
│   ├── judge.py                 # Jev requests                           (Chapter 13)
│   └── risk.py                  # The risk signal                        (Chapter 13)
└── chat/orchestrator.py         # A message end to end                   (Chapter 12)
```

## Primary sources

The primary sources cited throughout the book:

- Lewis et al., *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks* (2020), the paper that introduced the term RAG: <https://arxiv.org/abs/2005.11401>
- Malkov and Yashunin, *Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs* (the HNSW paper): <https://arxiv.org/abs/1603.09320>
- Cormack, Clarke and Büttcher, *Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods* (SIGIR 2009, the RRF paper): <https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf>
- pgvector documentation: <https://github.com/pgvector/pgvector>
- PostgreSQL full-text search documentation: <https://www.postgresql.org/docs/current/textsearch.html>
- OpenAI embeddings guide: <https://platform.openai.com/docs/guides/embeddings>
- Docling documentation: <https://docling-project.github.io/docling/> and chunking concepts: <https://docling-project.github.io/docling/concepts/chunking/>
- AI Cookbook (the tutorial code repository this project follows): <https://github.com/daveebbelaar/ai-cookbook>
  - Hybrid search; BM25, embeddings, RRF, reranking, NDCG and building an evaluation set: <https://github.com/daveebbelaar/ai-cookbook/tree/main/knowledge/hybrid-retrieval>
  - Extraction, chunking, embedding and search with Docling: <https://github.com/daveebbelaar/ai-cookbook/tree/main/knowledge/docling>
  - Agentic RAG (a tool-using agent, a structured answer with citations): <https://github.com/daveebbelaar/ai-cookbook/tree/main/knowledge/agentic-rag>
- PydanticAI (agent, tools, structured output): <https://ai.pydantic.dev/>
- TypeSafe AI / Jev documentation: <https://docs.typesafe.ai/introduction>

## How to read this book

- Concepts are explained from scratch; no prior knowledge is needed. If you meet an unknown term, see the [Glossary](glossary.md).
- Every chapter ends with a summary and a list of sources. To go deeper, go to the primary documents in the sources.
- Code samples are shortened; the full version is in the file the chapter names.
- The numbers (chunk counts, durations, costs) are values actually measured in this project.
