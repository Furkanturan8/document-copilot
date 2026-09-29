# Chapter 11 — Measuring Quality

> **In this chapter:** the difference between a RAG system that "looks like it works" and one that works, the verification methods used in this project, the bugs they found, and standard methods for measuring retrieval quality in numbers later on (recall, NDCG, an evaluation set).

## 11.1 RAG bugs are silent

In a classic program a bug usually shows up as a crash or an error message. In RAG most bugs are **silent**:

- If a table's title is wrong, nothing crashes; the search just cannot find that table.
- If a filtered search returns 3 results instead of 50, there is no error; the model only says "I could not find enough evidence".
- If a passage is indexed twice, results repeat, and nobody may notice.

So every step of this project followed one principle: **don't assume, measure.**

## 11.2 The verification methods we used

### 1. Coverage checks (counting)

"Is everything in the input also in the output?"

- HTML → Markdown: is every number and every word in the Markdown? (Chapter 3)
- HTML tables → clean tables: is every number of every financial table in the output? (Chapter 4)

### 2. Distribution statistics

Numbers over the whole corpus: how many chunks have a page, how many tables have no title, how many text chunks contain lines starting with `|` (a broken grid), does a page number ever go backwards, how many pages does a chunk span at most? An unexpected ratio (for example 13% section coverage, or a page range of `49-58`) was often the first sign of a bug.

### 3. Independent verification

A fill rate does not prove correctness: the page field can be 100% filled and wrong. So we located sampled chunks in the Markdown on disk, computed their page and section **by another method** and compared. We went through the mismatches one by one: some were real bugs (NVIDIA's table-of-contents lines), others were limits of the verification method (the same sentence occurring twice in a document).

### 4. Verifying the measuring tool too

The first version of the table coverage check joined cells without spaces and reported thousands of fake "losses". When a measurement looks too bad or too good, check the measuring tool first.

### 5. Unit tests, and "does the test really catch it?"

We wrote a test for every bug fixed (`backend/tests/`). For some we proved the test works **by temporarily removing the fix and watching the test fail**. For example, the test showing that an answer is still saved when the connection drops failed once the protection was removed. A test that never fails proves nothing.

### 6. Smoke test

`backend/scripts/smoke_retrieval.py` runs the 10 example questions from the client brief through search and prints the top 5 results with company, year, page and section: a quick check for a person to judge "does this make sense?". It found two big bugs (the filter trap and the AND trap).

### 7. Integration test

Tests marked `@pytest.mark.integration` run against the real database and OpenAI, for example "is the net sales by category table in the top 5 for Apple FY2024?". They are skipped in a normal test run (so they neither touch the network nor cost money) and run separately with `pytest -m integration`.

### 8. Budgeted smoke runs and benchmarks

In the answer-generation stage (Chapters 12 and 13) measuring became paid: each question costs $0.2–0.4 with `gpt-5.5`. So the measurement scripts are run on purpose, never enter the tests, and are guarded by a budget:

| Script | What it measures |
|---|---|
| `scripts/smoke_assistant.py --budget` | The client-brief questions end to end: tool calls, tokens, cost, latency, the validator result, citations. Stops before the next question once the budget is spent |
| `scripts/eval_judge.py` | The Jev risk signal: correct and false alarm rates with synthetic negatives (changed number, flipped direction, unrelated source) |
| `scripts/eval_router.py` | Jev question routing: whether any in-corpus question is wrongly turned away, on labelled questions |

Two habits paid off here too: a two-question **pilot** before an expensive run (to calibrate estimates with real numbers), and **comparing every rejected answer with its source text** (was the rejection right, or a bug in the measuring tool?).

## 11.3 The bugs we found

| Bug | How it was found | Effect | Fix | Chapter |
|---|---|---|---|---|
| Docling tables spread over 30 columns | HTML/Markdown comparison | The model reads the wrong column | Rebuild tables from the HTML | 4 |
| Microsoft header row taken for data | Counting tables without headers (~40/file) | Years are lost | A row of only years = header | 4 |
| `rowspan` ignored | Checking a sample table by eye | Headers shift by one column | Carry rowspan on the grid | 4 |
| Range dashes merge columns | Counting "value collisions" | Two values in one cell | A short dash between two values of the same kind = range | 4 |
| Table titles are footers/unit lines | Title-type distribution (10% wrong) | Meaningless titles in search and citations | Skip "non-title" lines | 4 |
| Table continuation pieces indexed with the broken grid | Classifying chunks that contain tables | The same figure twice; noise | In-place replacement with placeholders | 5 |
| Rich-cell content indexed again as text | "iPhone (1) / Mac (1)" in the smoke test | 524 duplicate chunks | `visited` marking | 5 |
| No page/section information | Fill-rate measurement (0% / 13%) | Citations without a page | Track footers and Item headings over the whole document | 5 |
| Table-of-contents and index numbers taken for footers/headings | Independent verification, a "49-58" range | Wrong page and section | Dense-run rule | 5 |
| Filtered vector search returns 3 results | "3 passages instead of 10" in the smoke test | Evidence disappears | Iterative scan + re-sort | 7 |
| Re-sort skipped | Order check | Results out of order | `ORDER BY distance + 0` | 7 |
| Full-text search returns zero results | Counting hits per question | Keyword search disabled | OR + matched-terms ranking | 8 |
| Link noise | `[Table of Contents](#…)` in the smoke test | Noisy results | Reduce links to their text | 5 |

The answer-generation stage produced the same kind of silent bugs:

| Bug | How it was found | Effect | Fix | Chapter |
|---|---|---|---|---|
| Read tools cut text at 800 characters | Measuring chunk lengths (70.7% are longer) | The model cannot quote what it never sees | Read tools return full text | 12 |
| A non-breaking hyphen (U+2011) gets correct excerpts rejected | Testing with another model, comparing a rejected excerpt with its source | A correct answer shown as an error | Hyphen variants normalized | 12 |
| Separator-row difference in a table excerpt | Same method | A correct excerpt rejected | Table markup ignored in the comparison | 12 |
| The model drops a sentence from inside a long excerpt | Comparing every rejection with its source in the 10-question run | The answer is rightly rejected | Instructions: short excerpts, nothing left out | 12 |
| An old year for a question without a year | Cheap-model measurement | A wrong but verified-looking answer | Instructions: latest year, and say so | 12 |
| A partly in-corpus question turned away | 48-question routing benchmark | The answerable part is refused | No short-circuit when a corpus company is named | 13 |

None of the bugs in these tables announced itself with an error message. All were found by counting, comparing, or looking carefully at results.

## 11.4 Advanced: measuring retrieval quality in numbers

Our smoke test is qualitative; it relies on a person's eye. Quantitative measures exist for comparing systems.

### Recall@k

"Is the passage with the right answer in the top k results?" The simplest and most intuitive measure. If the right passage is in the top 10 for 42 of 50 test questions, recall@10 = 0.84.

### NDCG@10

Recall only asks "is it there?"; **rank** does not matter. NDCG (Normalized Discounted Cumulative Gain) accounts for rank: a relevant passage at position 1 is worth much more than one at position 10. Following the cookbook's explanation:

- Each relevant passage contributes its score discounted by `1 / log₂(rank + 1)`: position 1 counts fully (1.0), position 10 only 0.289.
- The sum of these contributions is the **DCG**.
- The DCG of the perfect ordering is the **IDCG**.
- **NDCG = DCG / IDCG**, between 0 and 1; 1 means a perfect ordering.

In the cookbook's example, a query with 3 relevant documents has DCG@10 = 1.789 and IDCG@10 = 2.131, so NDCG@10 ≈ 0.84.

### Building your own evaluation set

Without a ready test set (our situation), the cookbook suggests:

1. Pick sample passages from the corpus (~100 to start).
2. Have an LLM write, for each passage, "a realistic question this passage answers". An important warning: the question must not rephrase the passage's first sentence, or keyword search will look artificially good.
3. Save the (question, correct passage) pairs.
4. Optionally: have an LLM label the search system's top 20 results for each question as relevant or not, so a question can have several correct passages.
5. Compare settings (semantic, full-text, hybrid, reranking, chunk sizes) on this set.

According to the cookbook, a quick 50-question check costs under a cent, and a meaningful 100–200-question comparison about $0.05. The absolute numbers will not match published benchmarks, but **the ranking between methods is meaningful for your own data.**

This could be a sensible next step for the project: showing in numbers how the improvements in this book (OR search, table titles and so on) affected retrieval quality.

## Summary

- RAG bugs are mostly silent; they are found only by measuring.
- Coverage checks, distribution statistics, independent verification, tests, smoke tests and budgeted benchmarks were used together, and the measuring tools themselves were verified.
- The project found 13 significant bugs in retrieval and ingestion and 6 in answer generation; none produced an error message.
- Recall@k and NDCG@10 are the quantitative measures; generating your own evaluation set with an LLM is cheap and effective.

## Sources

- Cookbook, NDCG explained and a guide to building an evaluation set: <https://github.com/daveebbelaar/ai-cookbook/tree/main/knowledge/hybrid-retrieval/docs>
- Code: `backend/tests/`, `backend/scripts/smoke_retrieval.py`, `smoke_assistant.py`, `eval_judge.py`, `eval_router.py`

---
[← Ingestion pipeline and database](10-ingestion-and-database.md) · Next chapter: [Answer generation and grounding →](12-answer-generation-and-grounding.md)
