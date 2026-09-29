# Document Copilot

An internal AI chatbot that lets analysts query a corpus of documents in plain English and get sourced, citable answers.

## The client

**Driftwood Capital** — fictional independent investment research firm. Their analysts spend half their week reading 10-Ks and 10-Qs before they can produce any original analysis. Document Copilot eats that intake work so they can skip straight to insight.

Full brief: [docs/client-brief.md](docs/client-brief.md)

## Demo

Screen recordings of the running app. Click an animation to open the full-quality video.

Every question first goes to **[Jev](https://docs.typesafe.ai/introduction)**, TypeSafe AI's typed-decision model. In one request (~0.4 s, ~\$0.00003) Jev classifies the question's scope and whether it asks for investment advice, and code decides the route: questions the filings cannot answer get a fixed reply without running the agent (gpt-5.5, ~60 s and ~\$0.3 per question). In-corpus questions go to the agent; after its answer passes the deterministic validator, Jev also checks each claim against its sources as a non-blocking risk signal. Details: [architecture](docs/architecture.md), [Chapter 13](docs/tutorials/en/13-jev-typed-decisions.md).

### Cited answer

*What was Apple's total net sales in fiscal 2024?* → \$391.035 billion, cited to the FY2024 10-K.

[![Apple FY2024 net sales](docs/media/demo-apple-net-sales-2024.gif)](docs/media/demo-apple-net-sales-2024.mp4)

### Latest year when none is given

*What's Apple's revenue?* → uses the latest filing (FY2025, \$416.161 billion) and says so.

[![Apple latest revenue](docs/media/demo-apple-latest-revenue.gif)](docs/media/demo-apple-latest-revenue.mp4)

### Opening a cited passage

*How did NVIDIA's gross margin change from fiscal 2024 to fiscal 2025?* → 72.7% to 75.0%; the source panel shows the verbatim excerpt.

[![NVIDIA gross margin](docs/media/demo-nvidia-gross-margin.gif)](docs/media/demo-nvidia-gross-margin.mp4)

### Routed by Jev: advice and another company

*Should I buy NVIDIA stock now?*: Jev's `advice` probability is above 0.8, so a fixed refusal is returned. *What was Tesla's revenue in 2024?*: Jev's `scope` decision is `other_company`. Both are answered in under a second without running the agent.

![Advice refusal and out-of-corpus answer](docs/media/advice-and-out-of-corpus.png)

### Routed by Jev: data annual reports cannot contain

*What is Apple's current share price?*: Jev's `scope` decision is `outside_filings` (prices, forecasts and news are not in a 10-K), so the question is answered without running the agent.

![Share price question](docs/media/share-price-out-of-corpus.png)

### Insufficient evidence

*What were Apple's quarterly results for Q3 fiscal 2024?*: Jev sees an in-corpus question and sends it to the agent. The agent finds no quarterly figures in the 10-Ks and says so, with no citations.

![Insufficient evidence answer](docs/media/insufficient-evidence.png)

## Stack

| Layer              | Choice                                               |
| ------------------ | ---------------------------------------------------- |
| Backend            | Python + FastAPI                                     |
| Frontend           | Vite + React SPA + TypeScript                        |
| Database           | Supabase Postgres (users, chats, documents, chunks)  |
| Migrations         | SQLAlchemy models + Alembic                          |
| Retrieval          | Supabase `pgvector` + Postgres full-text search      |
| Auth               | Supabase Auth (email only)                           |
| Hosting            | Railway                                              |
| LLM + embeddings   | OpenAI                                               |

## Repo layout

```text
document-copilot/
├── AGENTS.md           # agent instructions (read first)
├── README.md           # this file
├── data/               # local corpus + download script (payloads gitignored)
├── docs/
│   ├── client-brief.md # the client one-pager
│   ├── architecture.md # system design, data model, grounding policy
│   ├── guides/         # Supabase, backend, frontend and Railway setup
│   ├── todos.md        # build plan by phase
│   └── tutorials/      # book-style RAG tutorial (en/, tr/)
├── backend/            # FastAPI service
└── frontend/           # React SPA (Vite)
```

## Prerequisites

Install these before setting up `backend/` or `frontend/`:

| Tool | Version | Used for | Install |
| ---- | ------- | -------- | ------- |
| [Python](https://www.python.org/downloads/) | 3.14+ | Backend runtime | OS package manager or python.org |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | latest | Backend deps + `data/download.py` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| [Node.js](https://nodejs.org/) | 23+ | Frontend toolchain | nodejs.org or `nvm install 23` |
| [pnpm](https://pnpm.io/installation) | latest | Frontend package manager | `corepack enable && corepack prepare pnpm@latest --activate` |

You also need accounts/keys for external services once the app is wired up. Start with [docs/guides/supabase-setup.md](docs/guides/supabase-setup.md) (account + project), then create an [OpenAI API key](https://platform.openai.com/api-keys) when the LLM layer is wired up.

## Running locally

Start with [docs/guides/supabase-setup.md](docs/guides/supabase-setup.md) (account + project), then create the env files.

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Fill in `backend/.env`:

- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`
- `DATABASE_URL`: the direct Supabase Postgres connection, not the transaction pooler (port 6543)
- `OPENAI_API_KEY`
- `ALLOWED_ORIGINS=http://localhost:5173`
- Optional: `TYPESAFE_API_KEY` turns on Jev question routing and the grounding risk signal; without it both are skipped

Fill in `frontend/.env`: `VITE_API_BASE_URL=http://localhost:8000`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`.

Install, migrate and run:

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload      # http://localhost:8000

cd frontend                               # in a second terminal
pnpm install
pnpm dev                                  # http://localhost:5173
```

Sign-up is disabled: create users in the Supabase dashboard (Authentication → Users → Add user).
The chat needs a loaded corpus; see [Loading the corpus](#loading-the-corpus).

Checks (free, no paid API calls):

```bash
cd backend && uv run ruff check . && uv run pytest
cd frontend && pnpm lint && pnpm build
```

Paid checks, run on purpose: `uv run python -m scripts.smoke_retrieval` (embeddings, fractions of a cent) and
`uv run python -m scripts.smoke_assistant --budget 1` (the agent on the client-brief questions, ~$0.2–0.4 each).

## Sample SEC data

Use the standalone downloader to fetch a small local 10-K sample from SEC EDGAR.
Edit the params at the top of `data/download.py`, especially `USER_AGENT`, then run:

```bash
uv run data/download.py
```

By default this downloads the latest 5 10-K filings for AAPL, MSFT, NVDA, AMZN, and GOOGL into year folders under `data/downloads/` and writes a `manifest.json`.
Downloaded files are gitignored; the `data/` folder itself stays in git for the script and notes.

## Loading the corpus

From raw SEC filings to searchable chunks. Every step is idempotent: re-running skips what is already loaded.

```bash
uv run data/download.py                                   # 1. 10-K HTML from SEC EDGAR -> data/downloads/
cd backend
uv run python ../data/convert_to_markdown.py              # 2. HTML -> Markdown with Docling (free, local)
uv run python -m ingest.load_source_documents             # 3. one source_documents row per filing (free)
uv run python -m ingest.chunk_and_embed --all --dry-run   # 4a. chunk only, to check (free)
uv run python -m ingest.chunk_and_embed --all             # 4b. chunk, embed (OpenAI, paid) and write
```

To update one filing after a parsing change: `uv run python -m ingest.chunk_and_embed --accession <accession number> --force`.
Embedding the 25 pilot filings (~16,500 chunks) cost well under $1; uploading the vectors to Supabase is the slow part.
