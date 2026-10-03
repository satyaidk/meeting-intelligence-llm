"""Database engine and session setup.

Vocabulary:
    Engine   - owns the connection pool; one per process.
    Session  - a "unit of work": collects changes, then commits them together
               in one transaction (or rolls all of them back on error).
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from actiongraph.storage.models import Base


def create_db_engine(url: str, *, echo: bool = False) -> Engine:
    connect_args = {}
    if url.startswith("sqlite"):
        # FastAPI may use a session from a different thread than the one that
        # opened the connection; SQLite needs explicit permission for that.
        connect_args["check_same_thread"] = False
        _ensure_sqlite_directory(url)

    engine = create_engine(url, echo=echo, connect_args=connect_args)

    if url.startswith("sqlite"):
        # SQLite ignores foreign keys unless asked, per connection.
        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection, _record):  # pragma: no cover - trivial
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def init_db(engine: Engine) -> None:
    """Create any missing tables. (A production system would use Alembic migrations.)"""
    Base.metadata.create_all(engine)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    # expire_on_commit=False keeps objects readable after commit, which is
    # convenient when an API handler returns them right after saving.
    return sessionmaker(bind=engine, expire_on_commit=False)


def _ensure_sqlite_directory(url: str) -> None:
    prefix = "sqlite:///"
    if url.startswith(prefix) and ":memory:" not in url:
        Path(url[len(prefix) :]).parent.mkdir(parents=True, exist_ok=True)
