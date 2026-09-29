# Glossary

Short explanations of the terms used in the book. The number in parentheses is the chapter that explains the term in detail.

| Term | Explanation |
|---|---|
| **Accession number** | The unique number the SEC gives each filing; used to identify a document uniquely. (2) |
| **Agent** | A language model that can use tools: it decides itself when and with what to search, and reaches an answer over several turns. (12) |
| **Agentic RAG** | RAG in which the language model uses search tools itself, searching several times if needed and answering once it has enough evidence. (12) |
| **ANN (Approximate Nearest Neighbor)** | Finding the nearest vectors quickly without looking at all of them, at the price of a very small loss in accuracy. (7) |
| **BM25** | A classic ranking formula for keyword search; gives rare words more weight. (8) |
| **Cached input (prompt caching)** | The provider reading a repeated request prefix from its cache and billing it at a lower price. (12) |
| **Choice / Noul / Score** | Jev's question types: one of several options, a yes/no probability, or a score on an ordered scale. (13) |
| **Chunk** | A piece a document is split into for search; at most 512 tokens here. (5) |
| **Chunking** | Splitting a document into pieces. (5) |
| **CIK** | The permanent ID the SEC gives a company. (2) |
| **Citation** | The source passage a claim in an answer rests on: company, report, year, page, section. (1, 12) |
| **colspan / rowspan** | The number of columns and rows an HTML table cell spans. (4) |
| **Context window** | The maximum amount of text a language model can see at once. (1) |
| **Cosine similarity** | How much two vectors point the same way; 1 means the same, 0 unrelated. Distance = 1 − similarity. (6) |
| **DCG / NDCG** | Measures of ranked search quality that also account for the rank of relevant results. (11) |
| **Deferred column** | An ORM column loaded only when explicitly asked for; used for large columns, for performance. (7, 10) |
| **Deterministic validator** | The layer that checks an answer in code, without an LLM: markers, citations, retrieved chunks, verbatim excerpts. (12) |
| **Docling** | A library that turns documents (PDF, HTML…) into a structured model and Markdown. (3) |
| **DoclingDocument** | Docling's model of a document as a tree of items (text, table, group). (3) |
| **Dry run** | Trying an operation without paid calls or database writes. (10) |
| **ef_search** | The number of candidates kept during an HNSW search; 40 by default in pgvector. (7) |
| **Embedding** | An array of numbers (a vector) representing a text's meaning; 1536-dimensional here. (6) |
| **Fail closed** | Not showing the answer when a check fails: a controlled error instead of a polished but unsupported answer. (12) |
| **Fiscal year** | A company's accounting year; it need not match the calendar year. (2) |
| **Full-text search** | Search that matches words exactly; `tsvector`/`tsquery` in Postgres. (8) |
| **Generated column** | A column computed automatically from another column (`search_vector`). (8) |
| **GIN index** | An "inverted index": keeps the rows each word occurs in; speeds up full-text search. (8) |
| **Grounding** | Verifying in code that an answer rests on sources that were actually retrieved. (12) |
| **Hallucination** | A language model producing plausible-looking information that is not real. (1) |
| **HNSW** | An approximate nearest neighbor index that keeps vectors in a multi-layer graph. (7) |
| **Hybrid search** | Using semantic and full-text search together. (9) |
| **Hydrate** | Filling ids returned by a search with full row information. (9) |
| **Idempotent** | An operation whose result does not change when it is run again. (10) |
| **Indexing** | The phase, done in advance, that makes documents searchable. (1) |
| **Item** | The standard sections of a 10-K (Item 1 Business, Item 1A Risk Factors, Item 7 MD&A…). (2) |
| **Iterative index scan** | pgvector continuing to scan the index until enough results pass the filter. (7) |
| **Jev** | TypeSafe AI's model that produces no text and returns typed decisions with probabilities and confidence. (13) |
| **Lexeme** | The unit of a word left after stemming and normalization (`services` → `servic`). (8) |
| **LLM** | Large language model (GPT, Claude…). (1) |
| **LLM-as-judge** | Having a second model evaluate an answer, e.g. "does this source support this claim?". (13) |
| **Metadata** | A chunk's information besides its text: company, year, page, section, kind, table link. (5) |
| **Numeric checks** | Checking in code whether an answer's figures appear in the sources exactly, in other units, or computed. (12) |
| **Parsing** | Making a raw document usable as content and structure. (3) |
| **pgvector** | The Postgres extension that adds a vector type, distance operators and vector indexes. (7) |
| **Question routing** | Sending a question down a different path by its type; here advice and out-of-scope questions are answered without the agent. (13) |
| **RAG** | Retrieval-Augmented Generation: finding relevant documents and grounding the model's answer in them. (1) |
| **Reasoning tokens** | Thinking tokens a model produces internally before answering; the user never sees them, but they are billed. (12) |
| **Recall@k** | The share of questions whose right passage is in the top k results. (11) |
| **Reranking** | Re-ordering the first search results with a model that reads the question and the passage together. (9) |
| **Retrieval** | Finding the passages relevant to a question. (1, 9) |
| **Risk signal** | Telemetry that grades claims "none / warning / high" without ever blocking an answer. (13) |
| **RLS (Row Level Security)** | Row-level access rules in Postgres. (10) |
| **RRF (Reciprocal Rank Fusion)** | Combining ranked lists using only their ranks: `Σ 1/(k + rank)`, k = 60. (9) |
| **Semantic search** | Search that finds texts close in meaning through embeddings. (6, 7) |
| **Serializer** | The Docling component that writes document items as text; we wrote our own for tables. (5) |
| **Short-circuit** | Answering a question with a fixed answer without sending it to the agent (advice or out-of-scope questions). (13) |
| **Smoke test** | A quick, broad check that the system's basic function works. (11) |
| **Stemming** | Reducing words to their stem (`increased` → `increas`). (8) |
| **Stop words** | Frequent words without meaning that search skips (`the`, `to`). (8) |
| **Structured output** | A model returning a typed object with defined fields instead of free text (`GroundedAnswer`). (12) |
| **Synthetic negative** | A test case made by breaking a correct example in code, so the right answer is known (changing a figure, flipping a direction). (13) |
| **Token** | The unit in which language models process text; ~4 characters in English. (5) |
| **Tokenizer** | The tool that splits text into tokens; `tiktoken` with `cl100k_base` here. (5) |
| **Transaction** | A group of database operations that follows "all or nothing". (10) |
| **tsvector / tsquery** | Postgres types for searchable text and search queries. (8) |
| **Turn registry** | The list of chunks the tools returned during a message; the answer may cite only these. (12) |
| **Vector database** | A database that stores vectors and runs similarity search; we use Postgres + pgvector. (7) |
| **XBRL (inline)** | A standard that tags financial data for machines; a hidden section inside 10-K HTML. (2) |

---
[← Contents](README.md)
