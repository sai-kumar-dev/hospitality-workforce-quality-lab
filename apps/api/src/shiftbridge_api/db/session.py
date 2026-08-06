"""Database engine and transaction lifecycle."""

from __future__ import annotations

from collections.abc import Iterator  # noqa: TC003
from sqlite3 import Connection  # noqa: TC003

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import shiftbridge_api.models  # noqa: F401
from shiftbridge_api.db.base import Base


def _normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


class Database:
    """Own an engine so application instances remain independently testable."""

    def __init__(self, database_url: str) -> None:
        normalized_url = _normalize_database_url(database_url)
        engine_options: dict[str, object] = {
            "pool_pre_ping": True,
            "hide_parameters": True,
        }
        if normalized_url.startswith("sqlite"):
            engine_options["connect_args"] = {"check_same_thread": False}
            if normalized_url in {"sqlite://", "sqlite:///:memory:"}:
                engine_options["poolclass"] = StaticPool
        self.engine: Engine = create_engine(normalized_url, **engine_options)
        if normalized_url.startswith("sqlite"):
            event.listen(self.engine, "connect", _configure_sqlite_connection)
        self.session_factory = sessionmaker(
            bind=self.engine,
            class_=Session,
            expire_on_commit=False,
            autoflush=False,
        )

    def create_schema(self) -> None:
        """Create tables in local/test environments."""

        Base.metadata.create_all(self.engine)

    def drop_schema(self) -> None:
        """Drop all tables; callers must enforce environment safety."""

        Base.metadata.drop_all(self.engine)

    def session(self) -> Iterator[Session]:
        """Yield a session and always return its connection to the pool."""

        database_session = self.session_factory()
        try:
            yield database_session
        finally:
            database_session.close()

    def ping(self) -> None:
        """Verify the database can execute a bounded trivial query."""

        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))

    def dispose(self) -> None:
        """Dispose pooled connections at application shutdown."""

        self.engine.dispose()


def _configure_sqlite_connection(database_connection: Connection, _: object) -> None:
    """Enable relational integrity and wait briefly for concurrent writers."""

    cursor = database_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
    finally:
        cursor.close()
