"""SQLite schema for the grounded agent (entities.md, reliability-design.md NFR8.3).

U4 owns the ``ag_`` tables in the shared database file named by ``BRAHMA_DB_PATH``. The
connection is U3's ``cs_connect`` connection (U2 settings: WAL, busy timeout, foreign
keys on), so a walk references its case. A walk row holds the walk as JSON plus the
columns it is queried by; it is updated after every completed section so a failed walk
resumes where it stopped (FR5.9). A stopped explore lane can never reopen.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from brahma.cases.db import cs_connect
from brahma.platform.db import BUSY_TIMEOUT_MS

_SCHEMA = """
CREATE TABLE IF NOT EXISTS ag_walk (
    walk_id    TEXT PRIMARY KEY,
    case_id    TEXT NOT NULL REFERENCES cs_case(case_id),
    status     TEXT NOT NULL CHECK (status IN
        ('paused', 'answered', 'needs_data', 'out_of_knowledge', 'error')),
    body_json  TEXT NOT NULL,
    started_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ag_walk_case ON ag_walk(case_id, started_at);

CREATE TABLE IF NOT EXISTS ag_explore_lane (
    lane_id        TEXT PRIMARY KEY,
    walk_id        TEXT NOT NULL REFERENCES ag_walk(walk_id),
    branch_node_id TEXT NOT NULL,
    status         TEXT NOT NULL CHECK (status IN ('open', 'stopped')),
    body_json      TEXT NOT NULL,
    created_at     TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ag_explore_lane_one_open
    ON ag_explore_lane(walk_id, branch_node_id) WHERE status = 'open';

CREATE TRIGGER IF NOT EXISTS ag_explore_lane_no_reopen BEFORE UPDATE ON ag_explore_lane
WHEN OLD.status = 'stopped'
BEGIN SELECT RAISE(ABORT, 'ag_explore_lane: a stopped lane cannot change'); END;

CREATE TRIGGER IF NOT EXISTS ag_explore_lane_no_delete BEFORE DELETE ON ag_explore_lane
BEGIN SELECT RAISE(ABORT, 'ag_explore_lane rows are kept'); END;

CREATE TABLE IF NOT EXISTS ag_traverse_choice (
    choice_id  TEXT PRIMARY KEY,
    walk_id    TEXT NOT NULL REFERENCES ag_walk(walk_id),
    tier_id    TEXT NOT NULL,
    node_id    TEXT NOT NULL,
    body_json  TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ag_traverse_choice_walk
    ON ag_traverse_choice(walk_id, created_at);
"""


def ensure_ag_schema(conn: sqlite3.Connection) -> None:
    """Create any missing ``ag_`` table, index or trigger. Running it again changes nothing."""
    conn.executescript(_SCHEMA)


def ag_connect(
    path: str | Path | None = None, busy_timeout_ms: int = BUSY_TIMEOUT_MS
) -> sqlite3.Connection:
    """Open the shared database with the ``pf_``, ``cs_`` and ``ag_`` tables."""
    conn = cs_connect(path, busy_timeout_ms=busy_timeout_ms)
    ensure_ag_schema(conn)
    return conn
