FROM python:3.14-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Pinned like every other dependency here, not :latest.
COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /uvx /bin/

# Dependencies first, so code changes reuse this layer. --no-dev leaves out Docling:
# ingestion runs from a developer machine, not from the API image.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY alembic ./alembic
COPY alembic.ini ./
COPY app ./app
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# Railway sets PORT; 8000 is the local default.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
