"""Data access for ``pf_audit_entry`` and ``pf_session_record`` (BR1.1, BR1.3).

There are inserts and reads only; no update or delete path exists. ``add_*`` methods
run inside the caller's transaction; ``append`` opens its own ``BEGIN IMMEDIATE``.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from brahma.platform.audit.models import (
    AuditEntry,
    AuditEntryIn,
    SessionFilter,
    SessionRecord,
    SessionRecordIn,
    SessionSummary,
)
from brahma.platform.base import new_id, to_json, utc_now
from brahma.platform.db import transaction

LABEL_LENGTH = 80


def _like_pattern(text: str) -> str:
    escaped = text.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _search_text(session_id: str, record: SessionRecordIn) -> str:
    """Text the history search matches (BR1.3): inputs, finding names, answer label, ID."""
    names = [str(f.get("name", "")) for f in record.inputs.findings]
    parts = [session_id, record.inputs.text, *names, record.answer.summary]
    return "\n".join(parts).lower()


def _label(record: SessionRecordIn) -> str:
    text = " ".join(record.inputs.text.split())
    return text if len(text) <= LABEL_LENGTH else text[: LABEL_LENGTH - 1] + "…"


class AuditRepository:
    """Inserts and queries for the clinical record."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add_entry(self, entry: AuditEntryIn) -> str:
        """Insert one entry inside the current transaction; return its entryId."""
        entry_id = new_id("ae")
        self._conn.execute(
            "INSERT INTO pf_audit_entry (entry_id, kind, case_id, session_id, profile_id, "
            "pack_version, provider, model, benchmark_run_id, payload_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                entry_id,
                entry.kind,
                entry.case_id,
                entry.session_id,
                entry.profile_id,
                entry.pack_version,
                entry.provider,
                entry.model,
                entry.benchmark_run_id,
                to_json(entry.payload),
                utc_now(),
            ),
        )
        return entry_id

    def append(self, entry: AuditEntryIn) -> str:
        """Insert one entry in its own ``BEGIN IMMEDIATE`` transaction."""
        with transaction(self._conn):
            return self.add_entry(entry)

    def add_session(self, record: SessionRecordIn) -> str:
        """Insert one session record inside the current transaction; return its sessionId."""
        session_id = new_id("s")
        self._conn.execute(
            "INSERT INTO pf_session_record (session_id, case_id, walk_id, profile_id, "
            "pack_version, provider, model, outcome, benchmark_run_id, label, search_text, "
            "body_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                session_id,
                record.case_id,
                record.walk_id,
                record.profile_id,
                record.pack_version,
                record.provider,
                record.model,
                record.outcome,
                record.benchmark_run_id,
                _label(record),
                _search_text(session_id, record),
                record.model_dump_json(by_alias=True),
                utc_now(),
            ),
        )
        return session_id

    def list_sessions(self, flt: SessionFilter) -> list[SessionSummary]:
        """Session summaries newest first, filtered per BR1.3."""
        clauses: list[str] = []
        params: list[Any] = []
        if flt.outcome is not None:
            clauses.append("outcome = ?")
            params.append(flt.outcome)
        if flt.text:
            clauses.append("search_text LIKE ? ESCAPE '\\'")
            params.append(_like_pattern(flt.text))
        if flt.benchmark_run_id is not None:
            clauses.append("benchmark_run_id = ?")
            params.append(flt.benchmark_run_id)
        elif not flt.include_benchmark:
            clauses.append("benchmark_run_id IS NULL")
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._conn.execute(
            "SELECT session_id, case_id, created_at, label, outcome, pack_version "
            f"FROM pf_session_record{where} ORDER BY created_at DESC, rowid DESC",
            params,
        )
        return [
            SessionSummary(
                session_id=r["session_id"],
                case_id=r["case_id"],
                created_at=r["created_at"],
                label=r["label"],
                outcome=r["outcome"],
                pack_version=r["pack_version"],
            )
            for r in rows
        ]

    def get_session(self, session_id: str) -> SessionRecord | None:
        """The stored record, or None."""
        row = self._conn.execute(
            "SELECT session_id, body_json, created_at FROM pf_session_record WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if row is None:
            return None
        body = json.loads(row["body_json"])
        return SessionRecord.model_validate(
            {**body, "sessionId": row["session_id"], "createdAt": row["created_at"]}
        )

    def entries_for_session(self, session_id: str) -> list[AuditEntry]:
        """The session's audit entries in time order."""
        rows = self._conn.execute(
            "SELECT * FROM pf_audit_entry WHERE session_id = ? ORDER BY created_at, rowid",
            (session_id,),
        )
        return [AuditEntry.from_row(r, json.loads(r["payload_json"])) for r in rows]
