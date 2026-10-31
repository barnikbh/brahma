"""``AuditService``: contract C2 (append, record_session, list, get, export)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Literal

from brahma.platform.audit.models import (
    AuditEntryIn,
    SessionDetail,
    SessionFilter,
    SessionRecordIn,
    SessionSummary,
)
from brahma.platform.audit.pdf import PdfExporter
from brahma.platform.audit.repository import AuditRepository
from brahma.platform.db import pf_connect, transaction
from brahma.platform.errors import AuditInvalid, SessionNotFound
from brahma.platform.profiles import ProfileRepository

ExportFormat = Literal["json", "pdf"]


class AuditService:
    """The append-only clinical record. There is no update or delete operation (BR1.1)."""

    def __init__(self, conn: sqlite3.Connection, exporter: PdfExporter | None = None) -> None:
        self._conn = conn
        self._repo = AuditRepository(conn)
        self._profiles = ProfileRepository(conn)
        self._exporter = exporter or PdfExporter()
        self._profiles.seed()

    @classmethod
    def open(cls, path: str | Path | None = None) -> AuditService:
        """Open ``BRAHMA_DB_PATH`` (or ``path``) with U2's connection settings."""
        return cls(pf_connect(path))

    def close(self) -> None:
        """Close the underlying connection."""
        self._conn.close()

    def _check_profile(self, profile_id: str) -> None:
        if self._profiles.get(profile_id) is None:
            raise AuditInvalid(f"unknown profile: {profile_id}")

    def append(self, entry: AuditEntryIn) -> str:
        """Append one audit entry in one transaction and return its entryId.

        Raises AuditInvalid when the profile is unknown (BR1.2).
        """
        self._check_profile(entry.profile_id)
        return self._repo.append(entry)

    def record_session(self, record: SessionRecordIn) -> str:
        """Store a session record plus its ``session_recorded`` entry in one transaction.

        Returns the sessionId. Raises AuditInvalid when the profile is unknown (BR1.2).
        """
        self._check_profile(record.profile_id)
        with transaction(self._conn):
            session_id = self._repo.add_session(record)
            self._repo.add_entry(
                AuditEntryIn(
                    kind="session_recorded",
                    case_id=record.case_id,
                    session_id=session_id,
                    profile_id=record.profile_id,
                    pack_version=record.pack_version,
                    provider=record.provider,
                    model=record.model,
                    benchmark_run_id=record.benchmark_run_id,
                    payload={"walkId": record.walk_id, "outcome": record.outcome},
                )
            )
        return session_id

    def list_sessions(self, flt: SessionFilter | None = None) -> list[SessionSummary]:
        """History newest first; benchmark sessions hidden unless asked for (BR1.3)."""
        return self._repo.list_sessions(flt or SessionFilter())

    def get_session(self, session_id: str) -> SessionDetail:
        """The record and its audit entries in time order. Raises SessionNotFound."""
        record = self._repo.get_session(session_id)
        if record is None:
            raise SessionNotFound(session_id)
        return SessionDetail(record=record, entries=self._repo.entries_for_session(session_id))

    def export_session(self, session_id: str, fmt: ExportFormat) -> bytes:
        """The full session as UTF-8 JSON or as a PDF (BR1.4).

        Raises SessionNotFound for an unknown session and ExportFailed when the PDF
        cannot be produced; nothing partial is returned.
        """
        detail = self.get_session(session_id)
        if fmt == "pdf":
            return self._exporter.render(detail)
        if fmt != "json":
            raise ValueError(f"unknown export format: {fmt}")
        body = detail.model_dump(mode="json", by_alias=True)
        return json.dumps(body, ensure_ascii=False, indent=2).encode("utf-8")
