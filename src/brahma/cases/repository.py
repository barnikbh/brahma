"""Data access for the ``cs_`` tables (logical-components.md, BR1-BR4).

Every statement uses parameters. Write methods run inside the caller's transaction (the
service opens one ``BEGIN IMMEDIATE`` per operation), except ``acquire_lock`` and
``release_lock``, which are each one atomic transaction of their own.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from typing import Any

from brahma.cases.db import LOCK_EXPIRY_SECONDS
from brahma.cases.models import (
    Case,
    CaseStatus,
    CaseSummary,
    Finding,
    LockState,
    Message,
    Patient,
    TreatmentEdit,
)
from brahma.knowledge.models import PackVersionRef
from brahma.platform.base import to_json
from brahma.platform.db import transaction


def _like_pattern(text: str) -> str:
    escaped = text.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _case(row: sqlite3.Row) -> Case:
    pinned = None
    if row["pinned_pack"] is not None:
        pinned = PackVersionRef(pack=row["pinned_pack"], number=row["pinned_number"])
    return Case(
        case_id=row["case_id"],
        patient_id=row["patient_id"],
        owner_profile_id=row["owner_profile_id"],
        pinned_pack_version=pinned,
        origin=row["origin"],
        benchmark_run_id=row["benchmark_run_id"],
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _message(row: sqlite3.Row) -> Message:
    return Message(
        message_id=row["message_id"],
        case_id=row["case_id"],
        author=row["author"],
        kind=row["kind"],
        body=json.loads(row["body_json"]),
        form_kind=row["form_kind"],
        form_state=row["form_state"],
        created_at=row["created_at"],
    )


def _finding(row: sqlite3.Row) -> Finding:
    return Finding(
        finding_id=row["finding_id"],
        case_id=row["case_id"],
        kind=row["kind"],
        name=row["name"],
        value=json.loads(row["value_json"]),
        unit=row["unit"],
        entered_value=row["entered_value"],
        duration=row["duration"],
        validation_state=row["validation_state"],
        node_id=row["node_id"],
    )


def _edit(row: sqlite3.Row) -> TreatmentEdit:
    return TreatmentEdit(
        edit_id=row["edit_id"],
        case_id=row["case_id"],
        node_id=row["node_id"],
        original=json.loads(row["original_json"]),
        new_values=json.loads(row["new_values_json"]),
        editor_profile_id=row["editor_profile_id"],
        created_at=row["created_at"],
    )


class CaseRepository:
    """Parameterised SQL for patients, cases, messages, drafts, findings, locks and edits."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # --- patients and cases ----------------------------------------------------------

    def insert_patient(self, patient: Patient, now: str) -> None:
        self._conn.execute(
            "INSERT INTO cs_patient (patient_id, body_json, updated_at) VALUES (?, ?, ?)",
            (patient.patient_id, patient.model_dump_json(by_alias=True), now),
        )

    def update_patient(self, patient: Patient, now: str) -> None:
        self._conn.execute(
            "UPDATE cs_patient SET body_json = ?, updated_at = ? WHERE patient_id = ?",
            (patient.model_dump_json(by_alias=True), now, patient.patient_id),
        )

    def get_patient(self, patient_id: str) -> Patient | None:
        row = self._conn.execute(
            "SELECT body_json FROM cs_patient WHERE patient_id = ?", (patient_id,)
        ).fetchone()
        return Patient.model_validate_json(row["body_json"]) if row is not None else None

    def insert_case(self, case: Case) -> None:
        pinned = case.pinned_pack_version
        self._conn.execute(
            "INSERT INTO cs_case (case_id, patient_id, owner_profile_id, pinned_pack, "
            "pinned_number, origin, benchmark_run_id, status, synthetic, created_at, "
            "updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)",
            (
                case.case_id,
                case.patient_id,
                case.owner_profile_id,
                pinned.pack if pinned else None,
                pinned.number if pinned else None,
                case.origin,
                case.benchmark_run_id,
                case.status,
                case.created_at,
                case.updated_at,
            ),
        )

    def get_case(self, case_id: str) -> Case | None:
        row = self._conn.execute("SELECT * FROM cs_case WHERE case_id = ?", (case_id,)).fetchone()
        return _case(row) if row is not None else None

    def case_exists(self, case_id: str) -> bool:
        row = self._conn.execute("SELECT 1 FROM cs_case WHERE case_id = ?", (case_id,)).fetchone()
        return row is not None

    def set_pin(self, case_id: str, version: PackVersionRef, now: str) -> None:
        self._conn.execute(
            "UPDATE cs_case SET pinned_pack = ?, pinned_number = ?, updated_at = ? "
            "WHERE case_id = ?",
            (version.pack, version.number, now, case_id),
        )

    def set_status(self, case_id: str, status: CaseStatus, now: str) -> None:
        self._conn.execute(
            "UPDATE cs_case SET status = ?, updated_at = ? WHERE case_id = ?",
            (status, now, case_id),
        )

    def touch(self, case_id: str, now: str) -> None:
        self._conn.execute("UPDATE cs_case SET updated_at = ? WHERE case_id = ?", (now, case_id))

    def recent(self, owner_profile_id: str, limit: int = 20) -> list[CaseSummary]:
        """The owner's most recently updated clinic cases (FR12.1)."""
        rows = self._conn.execute(
            "SELECT c.case_id, c.patient_id, c.status, c.updated_at, p.body_json "
            "FROM cs_case c JOIN cs_patient p ON p.patient_id = c.patient_id "
            "WHERE c.owner_profile_id = ? AND c.origin = 'clinic' "
            "ORDER BY c.updated_at DESC, c.rowid DESC LIMIT ?",
            (owner_profile_id, limit),
        )
        return self._summaries(rows)

    def search(self, owner_profile_id: str, query: str) -> list[CaseSummary]:
        """The owner's clinic cases whose ID, a finding name or a pathway message matches."""
        pattern = _like_pattern(query.strip())
        rows = self._conn.execute(
            "SELECT c.case_id, c.patient_id, c.status, c.updated_at, p.body_json "
            "FROM cs_case c JOIN cs_patient p ON p.patient_id = c.patient_id "
            "WHERE c.owner_profile_id = ? AND c.origin = 'clinic' AND ("
            "  lower(c.case_id) LIKE ? ESCAPE '\\'"
            "  OR EXISTS (SELECT 1 FROM cs_finding f WHERE f.case_id = c.case_id "
            "             AND lower(f.name) LIKE ? ESCAPE '\\')"
            "  OR EXISTS (SELECT 1 FROM cs_message m WHERE m.case_id = c.case_id "
            "             AND m.kind = 'pathway' AND lower(m.body_json) LIKE ? ESCAPE '\\')"
            ") ORDER BY c.updated_at DESC, c.rowid DESC",
            (owner_profile_id, pattern, pattern, pattern),
        )
        return self._summaries(rows)

    @staticmethod
    def _summaries(rows: Iterable[sqlite3.Row]) -> list[CaseSummary]:
        return [
            CaseSummary(
                case_id=r["case_id"],
                patient_id=r["patient_id"],
                synthetic_name=json.loads(r["body_json"])["syntheticName"],
                status=r["status"],
                updated_at=r["updated_at"],
            )
            for r in rows
        ]

    # --- messages and drafts ---------------------------------------------------------

    def insert_message(self, message: Message) -> None:
        self._conn.execute(
            "INSERT INTO cs_message (message_id, case_id, author, kind, body_json, form_kind, "
            "form_state, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                message.message_id,
                message.case_id,
                message.author,
                message.kind,
                to_json(message.body),
                message.form_kind,
                message.form_state,
                message.created_at,
            ),
        )

    def get_message(self, case_id: str, message_id: str) -> Message | None:
        row = self._conn.execute(
            "SELECT * FROM cs_message WHERE case_id = ? AND message_id = ?",
            (case_id, message_id),
        ).fetchone()
        return _message(row) if row is not None else None

    def list_messages(self, case_id: str) -> list[Message]:
        rows = self._conn.execute(
            "SELECT * FROM cs_message WHERE case_id = ? ORDER BY created_at, rowid", (case_id,)
        )
        return [_message(r) for r in rows]

    def submit_form(self, message_id: str) -> bool:
        """Move an open form to submitted; False when it was not open."""
        cursor = self._conn.execute(
            "UPDATE cs_message SET form_state = 'submitted' "
            "WHERE message_id = ? AND form_state = 'open'",
            (message_id,),
        )
        return cursor.rowcount == 1

    def save_draft(self, case_id: str, message_id: str, values: dict[str, Any], now: str) -> None:
        self._conn.execute(
            "INSERT INTO cs_form_draft (message_id, case_id, values_json, updated_at) "
            "VALUES (?, ?, ?, ?) ON CONFLICT(message_id) DO UPDATE SET "
            "values_json = excluded.values_json, updated_at = excluded.updated_at",
            (message_id, case_id, to_json(values), now),
        )

    def get_drafts(self, case_id: str) -> dict[str, dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT message_id, values_json FROM cs_form_draft WHERE case_id = ? "
            "ORDER BY message_id",
            (case_id,),
        )
        return {r["message_id"]: json.loads(r["values_json"]) for r in rows}

    def delete_draft(self, message_id: str) -> None:
        self._conn.execute("DELETE FROM cs_form_draft WHERE message_id = ?", (message_id,))

    # --- findings --------------------------------------------------------------------

    def replace_findings(self, case_id: str, findings: list[Finding]) -> None:
        self._conn.execute("DELETE FROM cs_finding WHERE case_id = ?", (case_id,))
        for position, f in enumerate(findings):
            self._conn.execute(
                "INSERT INTO cs_finding (finding_id, case_id, position, kind, name, value_json, "
                "unit, entered_value, duration, validation_state, node_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    f.finding_id,
                    case_id,
                    position,
                    f.kind,
                    f.name,
                    to_json(f.value),
                    f.unit,
                    f.entered_value,
                    f.duration,
                    f.validation_state,
                    f.node_id,
                ),
            )

    def list_findings(self, case_id: str) -> list[Finding]:
        rows = self._conn.execute(
            "SELECT * FROM cs_finding WHERE case_id = ? ORDER BY position", (case_id,)
        )
        return [_finding(r) for r in rows]

    # --- tab lock (BR3) --------------------------------------------------------------

    def acquire_lock(
        self, case_id: str, tab_id: str, now: float, expiry: float = LOCK_EXPIRY_SECONDS
    ) -> LockState:
        """``held`` (and heartbeat refreshed) when free, ours or expired; else ``read_only``."""
        with transaction(self._conn):
            row = self._conn.execute(
                "SELECT tab_id, heartbeat_at FROM cs_tab_lock WHERE case_id = ?", (case_id,)
            ).fetchone()
            if row is not None and row["tab_id"] != tab_id and now - row["heartbeat_at"] <= expiry:
                return "read_only"
            self._conn.execute(
                "INSERT INTO cs_tab_lock (case_id, tab_id, heartbeat_at) VALUES (?, ?, ?) "
                "ON CONFLICT(case_id) DO UPDATE SET tab_id = excluded.tab_id, "
                "heartbeat_at = excluded.heartbeat_at",
                (case_id, tab_id, now),
            )
        return "held"

    def release_lock(self, case_id: str, tab_id: str) -> None:
        """Remove the lock only when ``tab_id`` holds it; otherwise do nothing."""
        with transaction(self._conn):
            self._conn.execute(
                "DELETE FROM cs_tab_lock WHERE case_id = ? AND tab_id = ?", (case_id, tab_id)
            )

    def lock_holder(self, case_id: str) -> str | None:
        row = self._conn.execute(
            "SELECT tab_id FROM cs_tab_lock WHERE case_id = ?", (case_id,)
        ).fetchone()
        return str(row["tab_id"]) if row is not None else None

    # --- treatment edits -------------------------------------------------------------

    def insert_edit(self, edit: TreatmentEdit) -> None:
        self._conn.execute(
            "INSERT INTO cs_treatment_edit (edit_id, case_id, node_id, original_json, "
            "new_values_json, editor_profile_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                edit.edit_id,
                edit.case_id,
                edit.node_id,
                to_json(edit.original),
                to_json(edit.new_values),
                edit.editor_profile_id,
                edit.created_at,
            ),
        )

    def latest_edit(self, case_id: str, node_id: str) -> TreatmentEdit | None:
        """The edit in effect for (case, node): the most recent one."""
        row = self._conn.execute(
            "SELECT * FROM cs_treatment_edit WHERE case_id = ? AND node_id = ? "
            "ORDER BY created_at DESC, rowid DESC LIMIT 1",
            (case_id, node_id),
        ).fetchone()
        return _edit(row) if row is not None else None
