"""SQLAlchemy 2.x engine, SessionLocal, and FastAPI dependency.

ponytail: SQLite check_same_thread=False because FastAPI + middleware share
the engine across threads via the request threadpool. Single-worker only.
"""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


_engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {},
)


def get_engine():
    """Re-read DATABASE_URL from env (test fixtures override it)."""
    import os

    url = os.getenv("DATABASE_URL", settings.database_url)
    return create_engine(
        url,
        connect_args={"check_same_thread": False} if url.startswith("sqlite") else {},
    )


SessionLocal = sessionmaker(bind=get_engine(), autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()