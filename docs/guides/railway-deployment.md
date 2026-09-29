# Railway deployment

Two Railway services from one project, each built from its own Dockerfile:

- `document-copilot-backend` from `backend/`: FastAPI + Uvicorn.
- `document-copilot-frontend` from `frontend/`: the Vite build served by Caddy.

Supabase stays hosted at Supabase; do not add Railway Postgres.

## Before Railway

- The repo pushed to GitHub (or the Railway CLI linked to the local repo).
- A Supabase project ([Supabase setup](supabase-setup.md)) with the schema migrated and the corpus loaded. If production uses the same Supabase project as development, both are already done.
- An OpenAI API key with credit. Each chat answer costs about $0.2–0.4 with `gpt-5.5`.
- Optional: a TypeSafe API key for Jev question routing and the grounding risk signal.

## Backend service

1. Railway → **New Project** → **Deploy from GitHub repo** → this repo. Name the service `document-copilot-backend`.
2. **Settings**: Root Directory `/backend`, Healthcheck Path `/health`. Leave build and start commands empty; Railway uses `backend/Dockerfile`.
3. **Variables**:

```text
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_ANON_KEY=your-anon-public-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-secret-key
DATABASE_URL=postgresql://postgres:your-password@db.your-project-ref.supabase.co:5432/postgres
OPENAI_API_KEY=sk-...
ALLOWED_ORIGINS=http://localhost:5173
TYPESAFE_API_KEY=...          # optional
```

   `DATABASE_URL` must be the direct connection (port 5432); the app refuses the transaction pooler (6543).
4. **Settings → Deploy → Pre-deploy command**: `alembic upgrade head` (a no-op when the schema is current).
5. Deploy, then **Networking → Generate Domain**. `https://<backend>.up.railway.app/health` should return `{"status":"ok"}`.

## Frontend service

1. In the same project: **New → GitHub Repo** → this repo. Name it `document-copilot-frontend`.
2. **Settings**: Root Directory `/frontend`, Healthcheck Path `/health`.
3. **Variables**, set **before** the first deploy (they are baked into the build):

```text
VITE_API_BASE_URL=https://<backend>.up.railway.app
VITE_SUPABASE_URL=https://your-project-ref.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-public-key
```

4. Deploy, then generate a domain. `https://<frontend>.up.railway.app/health` should return `ok`.
5. Back in the backend variables: `ALLOWED_ORIGINS=https://<frontend>.up.railway.app` (add `,http://localhost:5173` to keep local development working), then redeploy the backend.

## Supabase

- **Authentication → URL Configuration**: Site URL `https://<frontend>.up.railway.app`; add `https://<frontend>.up.railway.app/*` to Redirect URLs (keep `http://localhost:5173/*` for local development).
- Sign-up is disabled in this project. Create pilot users under **Authentication → Users → Add user**.

## Corpus

Ingestion is a manual job from a developer machine, never from the API image (Docling is a dev dependency and is not installed there). With production values in `backend/.env`, follow [Loading the corpus](../../README.md#loading-the-corpus). Skip it when production shares the development Supabase project.

## Notes

- Do not set `PORT`; Railway provides it and both containers bind to it.
- After changing a `VITE_*` variable, redeploy the frontend; the old values stay in the built bundle otherwise.
- The frontend `/health` route sits before the SPA fallback in `frontend/Caddyfile`, so the health check gets `ok`, not `index.html`.

## Final check

1. Open the frontend URL and sign in with a pilot user.
2. Ask a corpus question (e.g. "What was Apple's total net sales in fiscal 2024?") and click a citation.
3. Ask "Should I buy NVIDIA stock?": with `TYPESAFE_API_KEY` set, the refusal arrives within about a second, without an agent run.
4. Reload the page: the thread and its citations are still there.
