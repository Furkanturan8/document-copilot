"""SQLAlchemy engine and sessions for direct Postgres access (retrieval, ingestion)."""

from collections.abc import Iterator
from contextlib import contextmanager
from functools import cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from app.config import settings


@cache
def get_engine() -> Engine:
    # One engine per process: it owns the connection pool, and opening a new connection
    # to Supabase costs seconds.
    return create_engine(settings.sqlalchemy_database_url, pool_pre_ping=True)


@contextmanager
def get_session() -> Iterator[Session]:
    with Session(get_engine(), expire_on_commit=False) as session:
        yield session
