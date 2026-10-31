"""SQLite schema for cases and safety (entities.md, security-design.md NFR7.1).

U3 owns the ``cs_`` tables in the shared database file named by ``BRAHMA_DB_PATH``. The
connection is U2's ``pf_connect`` connection (WAL, busy timeout, foreign keys on), so a
``cs_`` write and its C2 audit entry can share one ``BEGIN IMMEDIATE`` transaction.

Messages and treatment edits are append-only: triggers refuse DELETE, and refuse UPDATE
except a form message's state moving from ``open`` to ``submitted`` (BR1.5).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from brahma.platform.db import BUSY_TIMEOUT_MS, pf_connect

LOCK_EXPIRY_SECONDS = 45.0

_SCHEMA = """
CREATE TABLE IF NOT EXISTS cs_patient (
    patient_id TEXT PRIMARY KEY,
    body_json  TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cs_case (
    case_id          TEXT PRIMARY KEY,
    patient_id       TEXT NOT NULL UNIQUE REFERENCES cs_patient(patient_id),
    owner_profile_id TEXT NOT NULL,
    pinned_pack      TEXT,
    pinned_number    TEXT,
    origin           TEXT NOT NULL CHECK (origin IN ('clinic', 'benchmark')),
    benchmark_run_id TEXT,
    status           TEXT NOT NULL CHECK (status IN
        ('new', 'needs_data', 'answered', 'out_of_knowledge', 'follow_up_due')),
    synthetic        INTEGER NOT NULL CHECK (synthetic = 1),
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL,
    CHECK (origin = 'clinic' OR benchmark_run_id IS NOT NULL),
    CHECK ((pinned_pack IS NULL) = (pinned_number IS NULL))
);

CREATE INDEX IF NOT EXISTS cs_case_owner ON cs_case(owner_profile_id, origin, updated_at);

CREATE TABLE IF NOT EXISTS cs_message (
    message_id TEXT PRIMARY KEY,
    case_id    TEXT NOT NULL REFERENCES cs_case(case_id),
    author     TEXT NOT NULL CHECK (author IN ('doctor', 'brahma', 'system')),
    kind       TEXT NOT NULL
        CHECK (kind IN ('text', 'form', 'form_answer', 'pathway', 'map_action')),
    body_json  TEXT NOT NULL,
    form_kind  TEXT,
    form_state TEXT CHECK (form_state IN ('open', 'submitted')),
    created_at TEXT NOT NULL,
    CHECK ((kind = 'form') = (form_state IS NOT NULL))
);

CREATE INDEX IF NOT EXISTS cs_message_case ON cs_message(case_id, created_at);

CREATE TABLE IF NOT EXISTS cs_form_draft (
    message_id  TEXT PRIMARY KEY REFERENCES cs_message(message_id),
    case_id     TEXT NOT NULL REFERENCES cs_case(case_id),
    values_json TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cs_finding (
    finding_id       TEXT PRIMARY KEY,
    case_id          TEXT NOT NULL REFERENCES cs_case(case_id),
    position         INTEGER NOT NULL,
    kind             TEXT NOT NULL,
    name             TEXT NOT NULL,
    value_json       TEXT NOT NULL,
    unit             TEXT,
    entered_value    TEXT,
    duration         TEXT,
    validation_state TEXT NOT NULL
        CHECK (validation_state IN ('ok', 'invalid', 'conflict', 'confirm_range')),
    node_id          TEXT
);

CREATE INDEX IF NOT EXISTS cs_finding_case ON cs_finding(case_id, position);
CREATE INDEX IF NOT EXISTS cs_finding_name ON cs_finding(name);

CREATE TABLE IF NOT EXISTS cs_tab_lock (
    case_id      TEXT PRIMARY KEY REFERENCES cs_case(case_id),
    tab_id       TEXT NOT NULL,
    heartbeat_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS cs_treatment_edit (
    edit_id           TEXT PRIMARY KEY,
    case_id           TEXT NOT NULL REFERENCES cs_case(case_id),
    node_id           TEXT NOT NULL,
    original_json     TEXT NOT NULL,
    new_values_json   TEXT NOT NULL,
    editor_profile_id TEXT NOT NULL,
    created_at        TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS cs_treatment_edit_case
    ON cs_treatment_edit(case_id, node_id, created_at);

CREATE TRIGGER IF NOT EXISTS cs_message_no_delete BEFORE DELETE ON cs_message
BEGIN SELECT RAISE(ABORT, 'cs_message rows are append-only'); END;

CREATE TRIGGER IF NOT EXISTS cs_message_form_state_only BEFORE UPDATE ON cs_message
WHEN NOT (
    OLD.form_state = 'open' AND NEW.form_state = 'submitted'
    AND NEW.message_id IS OLD.message_id
    AND NEW.case_id IS OLD.case_id
    AND NEW.author IS OLD.author
    AND NEW.kind IS OLD.kind
    AND NEW.body_json IS OLD.body_json
    AND NEW.form_kind IS OLD.form_kind
    AND NEW.created_at IS OLD.created_at
)
BEGIN SELECT RAISE(ABORT, 'cs_message may only move a form from open to submitted'); END;

CREATE TRIGGER IF NOT EXISTS cs_treatment_edit_no_update BEFORE UPDATE ON cs_treatment_edit
BEGIN SELECT RAISE(ABORT, 'cs_treatment_edit rows are append-only'); END;

CREATE TRIGGER IF NOT EXISTS cs_treatment_edit_no_delete BEFORE DELETE ON cs_treatment_edit
BEGIN SELECT RAISE(ABORT, 'cs_treatment_edit rows are append-only'); END;
"""


def ensure_cs_schema(conn: sqlite3.Connection) -> None:
    """Create any missing ``cs_`` table, index or trigger. Running it again changes nothing."""
    conn.executescript(_SCHEMA)


def cs_connect(
    path: str | Path | None = None, busy_timeout_ms: int = BUSY_TIMEOUT_MS
) -> sqlite3.Connection:
    """Open the shared database with U2's settings (WAL) and create the ``cs_`` tables.

    The ``pf_`` tables come from ``pf_connect``, so the same connection can write a case
    change and its audit entry in one transaction.
    """
    conn = pf_connect(path, busy_timeout_ms=busy_timeout_ms)
    ensure_cs_schema(conn)
    return conn
