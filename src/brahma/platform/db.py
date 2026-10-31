"""SQLite connection and schema for the platform (security-design.md NFR7.1).

U2 owns the ``pf_`` tables in the shared database file named by ``BRAHMA_DB_PATH``.
The audit tables and the model call log are append-only: BEFORE UPDATE and BEFORE
DELETE triggers abort. This guards against application bugs; it is not tamper-proof
storage (anyone with the file can drop a trigger), so ``pf_connect`` recreates any
missing trigger each time it opens the file.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from pathlib import Path
from typing import Any

from brahma.platform.errors import AuditImmutable

DEFAULT_DB_PATH = "./data/brahma.db"
BUSY_TIMEOUT_MS = 5000
APPEND_ONLY_TABLES = ("pf_audit_entry", "pf_session_record", "pf_model_call_log")
_APPEND_ONLY_MESSAGE = "rows are append-only"

_log = logging.getLogger("brahma.platform.db")


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

    The server shares one connection across its worker threads, and
    ``check_same_thread=False`` alone does not make that safe: two threads
    beginning a transaction together fail with "cannot start a transaction
    within a transaction" (seen as a 500). Every statement runs to completion
    under this connection's re-entrant lock, and ``transaction`` holds it for
    the whole block, so overlapping requests queue instead of failing.
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
CREATE TABLE IF NOT EXISTS pf_profile (
    profile_id        TEXT PRIMARY KEY,
    display_name      TEXT NOT NULL,
    role              TEXT NOT NULL CHECK (role IN ('doctor', 'reviewer', 'system')),
    specialty         TEXT,
    demo_registration TEXT,
    listed            INTEGER NOT NULL CHECK (listed IN (0, 1))
);

CREATE TABLE IF NOT EXISTS pf_disclaimer_acceptance (
    acceptance_id      TEXT PRIMARY KEY,
    profile_id         TEXT NOT NULL REFERENCES pf_profile(profile_id),
    disclaimer_version TEXT NOT NULL,
    pack_version       TEXT NOT NULL,
    accepted_at        TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS pf_disclaimer_by_profile
    ON pf_disclaimer_acceptance(profile_id, disclaimer_version);

CREATE TABLE IF NOT EXISTS pf_audit_entry (
    entry_id         TEXT PRIMARY KEY,
    kind             TEXT NOT NULL,
    case_id          TEXT,
    session_id       TEXT,
    profile_id       TEXT NOT NULL REFERENCES pf_profile(profile_id),
    pack_version     TEXT,
    provider         TEXT,
    model            TEXT,
    benchmark_run_id TEXT,
    payload_json     TEXT NOT NULL,
    created_at       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS pf_audit_entry_created ON pf_audit_entry(created_at);
CREATE INDEX IF NOT EXISTS pf_audit_entry_case ON pf_audit_entry(case_id);
CREATE INDEX IF NOT EXISTS pf_audit_entry_session ON pf_audit_entry(session_id, created_at);

CREATE TABLE IF NOT EXISTS pf_session_record (
    session_id       TEXT PRIMARY KEY,
    case_id          TEXT NOT NULL,
    walk_id          TEXT NOT NULL,
    profile_id       TEXT NOT NULL REFERENCES pf_profile(profile_id),
    pack_version     TEXT NOT NULL,
    provider         TEXT NOT NULL,
    model            TEXT NOT NULL,
    outcome          TEXT NOT NULL
        CHECK (outcome IN ('answered', 'needs_data', 'out_of_knowledge', 'error')),
    benchmark_run_id TEXT,
    label            TEXT NOT NULL,
    search_text      TEXT NOT NULL,
    body_json        TEXT NOT NULL,
    created_at       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS pf_session_record_created ON pf_session_record(created_at);
CREATE INDEX IF NOT EXISTS pf_session_record_case ON pf_session_record(case_id);

CREATE TABLE IF NOT EXISTS pf_model_call_log (
    call_id       TEXT PRIMARY KEY,
    provider      TEXT NOT NULL,
    model         TEXT NOT NULL,
    purpose       TEXT NOT NULL,
    latency_ms    INTEGER NOT NULL CHECK (latency_ms >= 0),
    input_tokens  INTEGER,
    output_tokens INTEGER,
    attempts      INTEGER NOT NULL CHECK (attempts BETWEEN 1 AND 3),
    error         TEXT,
    created_at    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS pf_model_call_log_created ON pf_model_call_log(created_at);
"""


def _trigger_name(table: str, action: str) -> str:
    return f"{table}_no_{action.lower()}"


def _trigger_sql(table: str, action: str) -> str:
    return (
        f"CREATE TRIGGER IF NOT EXISTS {_trigger_name(table, action)} "
        f"BEFORE {action} ON {table} "
        f"BEGIN SELECT RAISE(ABORT, '{table} {_APPEND_ONLY_MESSAGE}'); END;"
    )


def _ensure_triggers(conn: sqlite3.Connection) -> None:
    """Create any append-only trigger that is missing, logging each one restored."""
    present = {
        row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'trigger'")
    }
    for table in APPEND_ONLY_TABLES:
        for action in ("UPDATE", "DELETE"):
            if _trigger_name(table, action) not in present:
                conn.execute(_trigger_sql(table, action))
                if present:
                    _log.warning("restored missing trigger %s", _trigger_name(table, action))


def default_db_path() -> str:
    """Return ``BRAHMA_DB_PATH`` (when set and non-empty) or ``./data/brahma.db``."""
    return os.environ.get("BRAHMA_DB_PATH") or DEFAULT_DB_PATH


def pf_connect(
    path: str | Path | None = None, busy_timeout_ms: int = BUSY_TIMEOUT_MS
) -> sqlite3.Connection:
    """Open the database with U2's settings, create U2's tables and restore its triggers.

    The connection uses ``isolation_level=None`` (autocommit) so each write controls its
    own transaction with ``BEGIN IMMEDIATE`` (see ``transaction``). It sets WAL
    journaling, a busy timeout and foreign keys on.
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
    conn.executescript(_SCHEMA)
    _ensure_triggers(conn)
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Run the block in one ``BEGIN IMMEDIATE`` transaction; roll back on any error.

    The connection's lock is held for the whole block, so two threads can never
    interleave their transactions. An append-only trigger firing inside the block
    surfaces as ``AuditImmutable``.
    """
    hold = conn.locked() if isinstance(conn, LockedConnection) else nullcontext(conn)
    with hold:
        conn.execute("BEGIN IMMEDIATE")
        try:
            yield conn
        except BaseException as exc:
            conn.execute("ROLLBACK")
            if isinstance(exc, sqlite3.IntegrityError) and _APPEND_ONLY_MESSAGE in str(exc):
                raise AuditImmutable(str(exc)) from exc
            raise
        conn.execute("COMMIT")
