# Document Copilot — implementation checklist

Work top to bottom. Each phase unlocks the next. Check items off as you go.

## Where to start: backend, frontend, or both?

**Start with foundation, then backend-led vertical slices.**

| Order | Why |
| ----- | --- |
| 1. Supabase + sample data | Everything persists here; you need a project and a corpus to test against. |
| 2. Backend schema + migrations | Auth, chat, retrieval, and citations all depend on the data model. |
| 3. Thin vertical slices | Wire auth, then a stubbed chat stream, then real RAG — each slice touches frontend + backend together. |
| 4. Frontend in parallel (lightly) | Scaffold the SPA early, but don't build citation UI or chat polish until the backend can return real grounded answers. |

The critical path is **data model → ingestion → retrieval → LLM → citations**. The frontend is mostly a streaming chat shell with auth and citation display — it shouldn't get far ahead of working APIs.

---

## Phase 0 — Prerequisites & foundation

- [x] Install toolchain: Python 3.12+, `uv`, Node 20+, `pnpm` (see [README](../README.md))
- [X] Create Supabase project and collect credentials ([supabase-setup](guides/supabase-setup.md))
- [X] Create OpenAI API key (needed from Phase 6 onward)
- [X] Set `USER_AGENT` in `data/download.py` and download sample 10-K corpus:
  ```bash
  uv run data/download.py
  ```
- [X] Confirm `data/downloads/manifest.json` lists AAPL, MSFT, NVDA, AMZN, GOOGL filings (2021–2025)

---

## Phase 1 — Backend scaffold & database

Goal: a running FastAPI service with a migrated Supabase schema.

- [X] Init backend deps and project layout ([backend-setup](guides/backend-setup.md))
- [X] `app/config.py` — settings module, fail fast on missing env vars
- [X] `app/main.py` — FastAPI app, CORS, health check (`GET /health`)
- [X] SQLAlchemy models in `app/database/models/`:
  - [X] `users`
  - [X] `source_documents`
  - [X] `document_chunks` (embedding + generated `tsvector`)
  - [X] `chat_threads`
  - [X] `chat_messages`
  - [X] `message_citations`
- [X] Alembic init + first migration:
  - [X] `create extension if not exists vector`
  - [X] `vector(1536)` embedding column
  - [X] generated `tsvector` column on chunks
  - [X] HNSW index (vector) + GIN index (full-text)
  - [X] RLS policies (users see only their own chats)
- [X] `uv run alembic upgrade head` against Supabase direct connection
- [X] `app/database/supabase.py` — user-scoped and service-role clients
- [X] Verify: `uv run uvicorn app.main:app --reload` → health check returns 200

---

## Phase 2 — Auth (full stack)

Goal: analysts can sign in with email; backend rejects unauthenticated requests.

**Backend**

- [X] `app/auth/dependencies.py` — verify `Authorization: Bearer <supabase_jwt>`, expose `get_current_user`
- [X] Reject missing/expired tokens with `401` before any chat or retrieval work

**Frontend**

- [X] Scaffold Vite + React + TypeScript + Tailwind + shadcn ([frontend-setup](guides/frontend-setup.md))
- [X] `src/lib/env.ts` — validate `VITE_API_BASE_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`
- [X] `src/lib/supabase.ts` — browser Supabase client
- [X] `src/lib/http.ts` + `src/lib/api.ts` — fetch wrapper with automatic bearer token
- [X] Sign-in page (email only, no SSO) + request-access page — public sign-up is disabled in Supabase; admins create users in Dashboard → Authentication → Users → Add user (Auto Confirm)
- [X] Protected routes — redirect unauthenticated users to login
- [X] Verify: sign up, sign in, token reaches backend on a test authenticated endpoint

---

## Phase 3 — Chat shell (vertical slice, stubbed)

Goal: end-to-end chat UI streaming from FastAPI, no real retrieval yet.

**Backend**

- [X] Chat thread CRUD: list threads, create thread, load message history
- [X] `POST /chat/stream` — accepts AI SDK message format, streams a stubbed assistant reply
- [X] Persist user + assistant messages to `chat_messages` after stream completes
- [X] `403` when user accesses another user's thread
- [X] `DELETE /chat/threads/{id}` — delete a thread (added 2026-09-28 to match the reference)

**Frontend**

- [X] React Router: login, chat list, chat thread routes
- [X] AI SDK chat primitives pointed at `POST /chat/stream` with Supabase bearer token
- [X] Thread sidebar (past conversations)
- [X] Basic message list + input + streaming indicator
- [X] Verify: create thread, send message, see streamed stub response, reload and see history

---

## Phase 4 — Ingestion pipeline

Goal: SEC filings in the corpus are parsed, chunked, embedded, and stored in Supabase.

- [X] `ingest/` scripts (or CLI entrypoint) for one-off corpus loading
  - [X] `data/convert_to_markdown.py` — Docling HTML → Markdown for all filings into `data/markdown/<year>/` (run: `cd backend && uv run python ../data/convert_to_markdown.py`)
  - [X] `ingest/load_source_documents.py` — source stage: registers `source_documents` (metadata + Docling Markdown) in Supabase (run: `cd backend && uv run python -m ingest.load_source_documents`)
  - [X] Chunking stage (`ingest/chunk_and_embed.py`): per document, one transaction writes `document_tables` + `document_chunks` (+ embeddings) together and sets `ingested_at` last, so derived artifacts are always replaced as a unit
- [X] HTML → normalized Markdown extraction (preserve page/section metadata)
  - [X] Tables: Docling's Markdown tables repeat colspan cells and split `$`/`%` into their own cells, so tables are re-extracted from the raw HTML (`ingest/sec_tables.py`) into the new `document_tables` table (as in the reference). Tables are written by the chunking stage, not the source stage. `content_markdown` keeps the raw Docling output.
  - [X] Page / section metadata (improved over the reference, decided 2026-09-28): computed on the whole document before chunking. `page` = the next page footer after an item ("35", "35.", "Apple Inc. \| 2024 Form 10-K \| 35"), stored as "13-14" when a chunk crosses a page break; `section` = the last `Item N.` heading before it, with the canonical 10-K item title. Table-of-contents and index listings are ignored. Result: page 100%, section 98% of chunks (was ~0% / ~13% with the reference logic).
- [X] Chunking strategy (size + overlap; store chunk index, page, section, ticker, filing type, year) — `ingest/chunking.py`: Docling HybridChunker (512 tokens, cl100k_base) for narrative text; one `table_row` chunk per clean table row (title + units + header + row). Improved over the reference (2026-09-28): Docling tables are matched to the clean tables up front and serialized as markers, so table rows land where the table was and no Docling grid is indexed twice; layout tables become plain text. Dry run: 17,031 chunks (≈2.6M tokens) for 25 filings, 0 narrative chunks with a Docling table grid (was ~60% of narrative chunks).
- [X] Write `source_documents` rows with filing metadata from `manifest.json`
- [X] Write `document_chunks` rows with text + metadata
- [X] OpenAI embedding generation → store `vector(1536)` per chunk
- [X] Generated `tsvector` populated for full-text search (11 chunks are signature underscores with an empty tsvector)
- [X] Idempotent re-run (skip already-ingested documents) — verified: second `--all` run skipped 25/25
- [X] Unit tests: chunking logic, metadata extraction (`tests/ingest/`)
- [X] Run ingestion on full sample corpus (25 filings × 5 companies) — 25 documents, 16,507 chunks (4,201 narrative + 12,306 table rows), 1,407 tables
- [X] Verify: chunks exist in Supabase; spot-check a known passage (e.g. Apple revenue mix table) — found on p.23, Item 7

---

## Phase 5 — Retrieval

Goal: a user question returns ranked, relevant source passages.

- [X] `retrieval/queries.py` — pgvector semantic search over `document_chunks`
- [X] `retrieval/queries.py` — Postgres full-text search over `search_vector` (keywords from `retrieval/keywords.py`: a small model picks ≤5 words, since `plainto_tsquery` ANDs every word)
- [X] `retrieval/fusion.py` — Reciprocal Rank Fusion in Python
- [X] `retrieval/retriever.py` — query → fused ranked passages + neighbor chunks (neighbors fetched in one query, not one per hit)
- [X] Unit tests: fusion ranking, query assembly (mock DB) — `tests/retrieval/`
- [X] Integration test (optional, `@pytest.mark.integration`): real query against ingested corpus — run with `uv run pytest -m integration`
- [X] Verify: test queries from [client-brief](client-brief.md) return relevant chunks (manual or scripted) — `uv run python -m scripts.smoke_retrieval`: 10/10 questions return 10 passages from the right company, section and years. Weak spots left for the agent (Phase 6) to compensate with follow-up searches: the Apple revenue-mix question ranks the table footnotes above the net-sales table rows, and the Microsoft capex question surfaces tax/debt passages.

---

## Phase 6 — LLM agent & grounding

Goal: grounded answers with enforced citations — the core product contract.

- [X] `assistant/instructions.md` — product contract (cite everything, refuse to invent, no stock picks); corpus scope lists only what is ingested (5 tickers, 10-K, FY2021–2025)
- [X] PydanticAI agent with typed deps (`DocumentAgentDeps`) and output (`GroundedAnswer`) — `assistant/agent.py`, async `run_document_agent`
- [X] Agent tools: `search_filings`, `read_chunks`, `read_chunk`, `read_surrounding_chunks` — search returns 800-char excerpts; read tools return full chunk text (70.7% of narrative chunks exceed 800 chars), kept whole within the 12,000-char limit
- [X] `chat/orchestrator.py` — one turn: retrieve → agent → validate → stream → persist. `answer_question` returns a `TurnOutcome` (answer, validation, registry, usage, messages); failed validation streams a controlled error and persists nothing; a disconnect during the agent run cancels it. No retry
- [X] `grounding/validator.py` — every citation maps to a retrieved passage; fail closed on violation. Deterministic only (no LLM judge, unlike the reference): marker/citation/registry integrity, verbatim excerpts, uncited money/percent lines; figure-not-in-source is a warning. Structured `ValidationResult` (code, severity, citation_index, message). No retry yet
- [X] `chat/streaming.py` — AI SDK-compatible stream (text deltas + citation metadata parts): transient `data-status` parts while the agent runs, `data-citation` parts after the text
- [X] Persist `message_citations` linked to assistant messages — rows built from the streamed `data-citation` parts
- [X] Unit tests: citation validation, grounding enforcement, message conversion — `tests/grounding/`, `tests/chat/test_orchestrator.py`, `tests/assistant/`
- [] Verify against [client-brief example questions](client-brief.md#example-analyst-questions):
  - [X] Answers cite specific filings and pages — gpt-5.5, `scripts/smoke_assistant.py`: 6/10 client-brief answers pass validation with filing/page/section citations; Q3, Q7 rejected (model edited long excerpts), Q6, Q8 hit the 200K-token limit
  - [] Under-specified questions get "not enough evidence" responses — instructions now say: no year → use the latest fiscal year and say so; not enough evidence → no citations. Jev routing turns away confident out-of-scope and advice questions. Needs one paid run to confirm
  - [X] Question 10 (generative AI margins) refuses to infer beyond filings — presents the evidence and declines the causal claim

---

## Phase 7 — Trust UI (citations & source passages)

Goal: analysts can verify every claim in one click — this is what makes the product usable.

- [X] Citation chips/links on assistant messages (company, filing type, date, page/section) — `CitationChip`, `CitationMarker`
- [X] Source passage panel — show underlying excerpt for selected citation — `SourcePassageSheet`
- [X] Empty states (no threads, no corpus match) — `ChatEmptyPage`; no-evidence answers render as normal replies
- [X] Error states (auth expired, retrieval failure, grounding failure, network/CORS) — `ChatError`, `lib/chat-errors.ts`
- [X] Loading/streaming status during assistant run — transient `data-status` parts via `onData` → `PipelineStatus`
- [] Verify: click a citation → see the exact passage from the filing

---

## Phase 8 — Pilot readiness

Goal: 5 senior analysts can use it for a week and report ≥3 hours saved per analyst per week.

- [X] README "Running locally" section — copy-paste commands for backend + frontend + env vars
- [X] Seed or document how to ingest/update the corpus — README "Loading the corpus"
- [] Smoke-test all 10 example questions from the client brief — last full run (before the excerpt-rule instructions): 6/10 pass; Q3, Q7 rejected for edited excerpts, Q6, Q8 hit the 200K-token limit. Rerun needs ~$3–4 of OpenAI credit
- [] Confirm chat history persists across sessions
- [] Confirm ~40-user scale assumptions (no hardcoded single-user shortcuts) — per-user auth and RLS, no single-user shortcuts. Limit: the default SQLAlchemy pool (5 + 10 overflow) makes turns wait for a connection beyond ~5–6 concurrent turns
- [X] Basic structured logging on backend (`structlog`) for debugging failed turns — `question_routing`, `grounding_validation`, `grounding_risk`, `chat_turn_agent_failed`
- [ ] Review latency: streaming starts within a few seconds for typical queries — status parts stream from the first second; the answer text arrives after 60–100 s with gpt-5.5; routed refusals under 1 s

---

## Phase 9 — Deployment (Railway)

- [] Railway: backend service (Uvicorn, env vars, `ALLOWED_ORIGINS`) — `backend/Dockerfile`, guide in `docs/guides/railway-deployment.md`
- [] Railway: frontend service (Vite build, `VITE_*` env vars at build time) — `frontend/Dockerfile` + `Caddyfile`
- [X] Supabase: re-enable email confirmation for production if disabled during dev — not applicable: sign-up is disabled; pilot users are created in the Supabase dashboard
- [] Run `alembic upgrade head` against production Supabase (direct connection)
- [] Run ingestion against production database
- [] End-to-end test on deployed URLs with a real Driftwood-style email account

---

## Quick reference

| Doc | Purpose |
| --- | ------- |
| [client-brief.md](client-brief.md) | What Driftwood needs and example questions |
| [architecture.md](architecture.md) | System design, data model, streaming contract |
| [guides/supabase-setup.md](guides/supabase-setup.md) | Hosted Postgres + Auth |
| [guides/backend-setup.md](guides/backend-setup.md) | FastAPI + Alembic commands |
| [guides/frontend-setup.md](guides/frontend-setup.md) | Vite + React scaffold commands |