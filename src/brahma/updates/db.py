"""SQLite schema for knowledge updates (entities.md, security-design.md).

U5 owns the ``up_`` tables in the shared database file named by ``BRAHMA_DB_PATH``. The
connection is U2's ``pf_connect`` connection, so a proposal's status change and its C2
audit entry can share one ``BEGIN IMMEDIATE`` transaction (NFR7.1).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from brahma.platform.db import BUSY_TIMEOUT_MS, pf_connect

_SCHEMA = """
CREATE TABLE IF NOT EXISTS up_linked_source (
    source_id       TEXT PRIMARY KEY,
    pack            TEXT NOT NULL,
    url             TEXT NOT NULL,
    title           TEXT NOT NULL,
    content_hash    TEXT,
    last_checked_at TEXT,
    last_status     TEXT NOT NULL CHECK (last_status IN ('new', 'ok', 'changed', 'failed')),
    UNIQUE (pack, url)
);

CREATE TABLE IF NOT EXISTS up_proposal (
    proposal_id         TEXT PRIMARY KEY,
    pack                TEXT NOT NULL,
    base_version        TEXT NOT NULL,
    target_version      TEXT NOT NULL,
    proposer_profile_id TEXT NOT NULL,
    origin              TEXT NOT NULL CHECK (origin IN ('doctor', 'drafted', 'scheduled')),
    change_set_json     TEXT NOT NULL,
    comment             TEXT NOT NULL,
    status              TEXT NOT NULL CHECK (status IN ('proposed', 'published', 'rejected')),
    source_id           TEXT REFERENCES up_linked_source(source_id),
    reviewer_profile_id TEXT,
    review_comment      TEXT,
    published_version   TEXT,
    created_at          TEXT NOT NULL,
    decided_at          TEXT,
    CHECK ((status = 'proposed') = (decided_at IS NULL)),
    CHECK ((status = 'published') = (published_version IS NOT NULL))
);

CREATE INDEX IF NOT EXISTS up_proposal_pack ON up_proposal(pack, status, created_at);

CREATE TABLE IF NOT EXISTS up_proposal_change (
    proposal_id    TEXT NOT NULL REFERENCES up_proposal(proposal_id),
    position       INTEGER NOT NULL,
    node_id        TEXT NOT NULL,
    before_json    TEXT,
    after_json     TEXT NOT NULL,
    source_passage TEXT,
    copy_flag      INTEGER NOT NULL CHECK (copy_flag IN (0, 1)),
    PRIMARY KEY (proposal_id, node_id)
);

CREATE TABLE IF NOT EXISTS up_thread (
    thread_id  TEXT PRIMARY KEY,
    pack       TEXT NOT NULL,
    profile_id TEXT NOT NULL,
    status     TEXT NOT NULL CHECK (status IN ('open', 'proposed', 'stuck')),
    rounds     INTEGER NOT NULL CHECK (rounds >= 0),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS up_thread_message (
    thread_id   TEXT NOT NULL REFERENCES up_thread(thread_id),
    position    INTEGER NOT NULL,
    role        TEXT NOT NULL CHECK (role IN ('doctor', 'assistant')),
    text        TEXT NOT NULL,
    proposal_id TEXT,
    created_at  TEXT NOT NULL,
    PRIMARY KEY (thread_id, position)
);

CREATE TABLE IF NOT EXISTS up_source_check_run (
    run_id      TEXT PRIMARY KEY,
    started_at  TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    checked     INTEGER NOT NULL CHECK (checked >= 0),
    changed     INTEGER NOT NULL CHECK (changed >= 0),
    failed      INTEGER NOT NULL CHECK (failed >= 0),
    errors_json TEXT NOT NULL
);
"""


def ensure_up_schema(conn: sqlite3.Connection) -> None:
    """Create any missing ``up_`` table or index. Running it again changes nothing."""
    conn.executescript(_SCHEMA)
    columns = {r[1] for r in conn.execute("PRAGMA table_info(up_proposal_change)")}
    if "source_url" not in columns:  # added with the update conversation; older files lack it
        conn.execute("ALTER TABLE up_proposal_change ADD COLUMN source_url TEXT")


def up_connect(
    path: str | Path | None = None, busy_timeout_ms: int = BUSY_TIMEOUT_MS
) -> sqlite3.Connection:
    """Open the shared database with U2's settings (WAL) and create the ``up_`` tables."""
    conn = pf_connect(path, busy_timeout_ms=busy_timeout_ms)
    ensure_up_schema(conn)
    return conn
