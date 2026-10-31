"""SQLite connection and schema for the knowledge graph (security-design.md NFR7.1, NFR8.2).

U1 owns the ``kg_`` tables in the shared database file named by ``BRAHMA_DB_PATH``.
Published rows are immutable: triggers refuse UPDATE and DELETE, except a pack version's
status moving from ``live`` to ``superseded``. A partial unique index allows only one
live version per pack.
"""

from __future__ import annotations

import os
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

DEFAULT_DB_PATH = "./data/brahma.db"
BUSY_TIMEOUT_MS = 5000


class _BufferedCursor:
    """A single-pass cursor over rows already fetched under the connection's lock.

    ``LockedConnection`` runs every statement to completion while holding the lock
    and hands back one of these, so no fetch can interleave with another thread's
    statement. It implements the cursor API Brahma uses: fetch one/many/all,
    iteration, ``rowcount``/``lastrowid``/``description``/``arraysize``, ``close``.
    """

    def __init__(self, cursor: sqlite3.Cursor, rows: list[Any]) -> None:
        self._rows = rows
        self._pos = 0
        self._closed = False
        self.description = cursor.description
        self.rowcount = cursor.rowcount
        self.lastrowid = cursor.lastrowid
        self.arraysize = cursor.arraysize

    def fetchone(self) -> Any:
        self._check_open()
        if self._pos >= len(self._rows):
            return None
        row = self._rows[self._pos]
        self._pos += 1
        return row

    def fetchmany(self, size: int | None = None) -> list[Any]:
        self._check_open()
        count = self.arraysize if size is None else max(size, 0)
        end = min(self._pos + count, len(self._rows))
        rows = self._rows[self._pos : end]
        self._pos = end
        return rows

    def fetchall(self) -> list[Any]:
        self._check_open()
        rows = self._rows[self._pos :]
        self._pos = len(self._rows)
        return rows

    def __iter__(self) -> Iterator[Any]:
        self._check_open()
        return self

    def __next__(self) -> Any:
        row = self.fetchone()
        if row is None:
            raise StopIteration
        return row

    def close(self) -> None:
        self._closed = True

    def _check_open(self) -> None:
        if self._closed:
            raise sqlite3.ProgrammingError("Cannot operate on a closed cursor.")


class LockedConnection(sqlite3.Connection):
    """A connection that serialises every statement across threads.

    The server shares one knowledge connection across its worker threads, and
    ``check_same_thread=False`` alone does not make that safe: two threads
    beginning a transaction together fail with "cannot start a transaction
    within a transaction" (seen as a 500). Every statement runs to completion
    under this connection's re-entrant lock, and ``KnowledgeRepository.transaction``
    holds it for the whole block, so overlapping requests queue instead of failing.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._db_lock = threading.RLock()

    @contextmanager
    def locked(self) -> Iterator[LockedConnection]:
        """Hold this connection's lock for the block (re-entrant)."""
        with self._db_lock:
            yield self

    def _buffered(self, cursor: sqlite3.Cursor) -> _BufferedCursor:
        rows = cursor.fetchall() if cursor.description is not None else []
        return _BufferedCursor(cursor, rows)

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Run the statement under the lock; rows come back buffered, never live."""
        with self._db_lock:
            return self._buffered(super().execute(*args, **kwargs))

    def executemany(self, *args: Any, **kwargs: Any) -> Any:
        """Run the statement under the lock; rows come back buffered, never live."""
        with self._db_lock:
            return self._buffered(super().executemany(*args, **kwargs))

    def executescript(self, *args: Any, **kwargs: Any) -> Any:
        """Run the script under the lock; rows come back buffered, never live."""
        with self._db_lock:
            return self._buffered(super().executescript(*args, **kwargs))

    def close(self) -> None:
        with self._db_lock:
            super().close()


_SCHEMA = """
CREATE TABLE IF NOT EXISTS kg_pack (
    pack_id   TEXT PRIMARY KEY,
    code      TEXT NOT NULL UNIQUE,
    name      TEXT NOT NULL UNIQUE,
    specialty TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS kg_pack_version (
    pack_version_id TEXT PRIMARY KEY,
    pack_id         TEXT NOT NULL REFERENCES kg_pack(pack_id),
    number          TEXT NOT NULL,
    major           INTEGER NOT NULL,
    minor           INTEGER NOT NULL,
    status          TEXT NOT NULL CHECK (status IN ('live', 'superseded')),
    published_at    TEXT NOT NULL,
    published_by    TEXT NOT NULL,
    change_summary  TEXT NOT NULL,
    based_on        TEXT REFERENCES kg_pack_version(pack_version_id),
    UNIQUE (pack_id, number)
);

CREATE UNIQUE INDEX IF NOT EXISTS kg_pack_version_one_live
    ON kg_pack_version(pack_id) WHERE status = 'live';

CREATE TABLE IF NOT EXISTS kg_source (
    source_id TEXT PRIMARY KEY,
    pack_id   TEXT NOT NULL REFERENCES kg_pack(pack_id),
    body_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS kg_node (
    pack_version_id TEXT NOT NULL REFERENCES kg_pack_version(pack_version_id),
    node_id         TEXT NOT NULL,
    type            TEXT NOT NULL,
    body_json       TEXT NOT NULL,
    PRIMARY KEY (pack_version_id, node_id)
);

CREATE INDEX IF NOT EXISTS kg_node_by_id ON kg_node(node_id);

CREATE TABLE IF NOT EXISTS kg_edge (
    pack_version_id TEXT NOT NULL REFERENCES kg_pack_version(pack_version_id),
    edge_id         TEXT NOT NULL,
    from_node_id    TEXT NOT NULL,
    to_node_id      TEXT NOT NULL,
    body_json       TEXT NOT NULL,
    PRIMARY KEY (pack_version_id, edge_id),
    FOREIGN KEY (pack_version_id, from_node_id) REFERENCES kg_node(pack_version_id, node_id),
    FOREIGN KEY (pack_version_id, to_node_id) REFERENCES kg_node(pack_version_id, node_id),
    CHECK (from_node_id <> to_node_id)
);

CREATE TABLE IF NOT EXISTS kg_comment (
    comment_id        TEXT PRIMARY KEY,
    node_id           TEXT NOT NULL,
    author_profile_id TEXT NOT NULL,
    text              TEXT NOT NULL,
    created_at        TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS kg_comment_by_node ON kg_comment(node_id, created_at);
"""

_IMMUTABLE_TABLES = ("kg_pack", "kg_node", "kg_edge", "kg_source")


def _immutability_triggers() -> str:
    statements = []
    for table in _IMMUTABLE_TABLES:
        for action in ("UPDATE", "DELETE"):
            statements.append(
                f"CREATE TRIGGER IF NOT EXISTS {table}_no_{action.lower()} "
                f"BEFORE {action} ON {table} "
                f"BEGIN SELECT RAISE(ABORT, '{table} rows are immutable'); END;"
            )
    statements.append(
        "CREATE TRIGGER IF NOT EXISTS kg_pack_version_no_delete "
        "BEFORE DELETE ON kg_pack_version "
        "BEGIN SELECT RAISE(ABORT, 'kg_pack_version rows are immutable'); END;"
    )
    statements.append(
        """
        CREATE TRIGGER IF NOT EXISTS kg_pack_version_status_only
        BEFORE UPDATE ON kg_pack_version
        WHEN NOT (
            OLD.status = 'live' AND NEW.status = 'superseded'
            AND NEW.pack_version_id IS OLD.pack_version_id
            AND NEW.pack_id IS OLD.pack_id
            AND NEW.number IS OLD.number
            AND NEW.major IS OLD.major
            AND NEW.minor IS OLD.minor
            AND NEW.published_at IS OLD.published_at
            AND NEW.published_by IS OLD.published_by
            AND NEW.change_summary IS OLD.change_summary
            AND NEW.based_on IS OLD.based_on
        )
        BEGIN
            SELECT RAISE(ABORT, 'kg_pack_version may only change status from live to superseded');
        END;
        """
    )
    return "\n".join(statements)


def default_db_path() -> str:
    """Return ``BRAHMA_DB_PATH`` or ``./data/brahma.db``. U1 reads no other setting (NFR5.1)."""
    return os.environ.get("BRAHMA_DB_PATH", DEFAULT_DB_PATH)


def kg_connect(
    path: str | Path | None = None, busy_timeout_ms: int = BUSY_TIMEOUT_MS
) -> sqlite3.Connection:
    """Open the database with U1's settings and create U1's tables if missing.

    The connection uses ``isolation_level=None`` so each write controls its own
    transaction with ``BEGIN IMMEDIATE``. It sets WAL journaling, a busy timeout
    (5 seconds unless a test passes a shorter one) and foreign keys on.
    """
    db_path = Path(path) if path is not None else Path(default_db_path())
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        str(db_path),
        isolation_level=None,
        timeout=busy_timeout_ms / 1000,
        check_same_thread=False,
        factory=LockedConnection,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(f"PRAGMA busy_timeout={int(busy_timeout_ms)}")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(_SCHEMA + _immutability_triggers())
    return conn
