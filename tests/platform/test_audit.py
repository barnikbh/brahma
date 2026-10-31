"""AuditService: record_session, history, detail and JSON/PDF export (BR1.1-BR1.4, NFR6.2)."""

from __future__ import annotations

import json
import re
import sqlite3
import zlib
from collections.abc import Iterator

import pytest

from brahma.platform.audit import AuditService, SessionFilter
from brahma.platform.audit.pdf import HEADER, PdfExporter, to_latin1_safe
from brahma.platform.errors import AuditInvalid, ExportFailed, SessionNotFound
from tests.platform.factories import make_entry, make_session

_STREAM = re.compile(rb"stream\r?\n(.*?)\r?\nendstream", re.DOTALL)


def _pdf_text(pdf: bytes) -> bytes:
    """Concatenate every page content stream, inflating the compressed ones."""
    chunks = []
    for raw in _STREAM.findall(pdf):
        try:
            chunks.append(zlib.decompress(raw))
        except zlib.error:
            chunks.append(raw)
    return b"\n".join(chunks)


@pytest.fixture
def audit(conn: sqlite3.Connection) -> Iterator[AuditService]:
    yield AuditService(conn)


def test_record_session_writes_record_and_entry(
    audit: AuditService, conn: sqlite3.Connection
) -> None:
    session_id = audit.record_session(make_session())

    detail = audit.get_session(session_id)
    assert detail.record.session_id == session_id
    assert detail.record.provider == "recorded"
    assert [e.kind for e in detail.entries] == ["session_recorded"]
    assert detail.entries[0].payload == {"walkId": "walk-001", "outcome": "answered"}
    assert conn.execute("SELECT COUNT(*) FROM pf_session_record").fetchone()[0] == 1


def test_unknown_profile_is_refused(audit: AuditService, conn: sqlite3.Connection) -> None:
    with pytest.raises(AuditInvalid, match="unknown profile"):
        audit.append(make_entry(profileId="p-stranger"))
    with pytest.raises(AuditInvalid, match="unknown profile"):
        audit.record_session(make_session(profileId="p-stranger"))
    assert conn.execute("SELECT COUNT(*) FROM pf_audit_entry").fetchone()[0] == 0


def test_append_and_list_sessions(audit: AuditService) -> None:
    entry_id = audit.append(make_entry(kind="sign_in"))
    session_id = audit.record_session(make_session())
    audit.record_session(make_session(benchmarkRunId="run-1", profileId="p-benchmark"))

    assert entry_id.startswith("ae-")
    assert [s.session_id for s in audit.list_sessions()] == [session_id]
    assert len(audit.list_sessions(SessionFilter(benchmark_run_id="run-1"))) == 1


def test_json_export_holds_record_and_entries(audit: AuditService) -> None:
    session_id = audit.record_session(make_session())

    exported = json.loads(audit.export_session(session_id, "json").decode("utf-8"))

    assert exported["record"]["sessionId"] == session_id
    assert exported["record"]["inputs"]["findings"][0]["unit"] == "µg/g"
    assert exported["entries"][0]["kind"] == "session_recorded"


def test_pdf_export_renders_symbols_and_both_header_strings(audit: AuditService) -> None:
    session_id = audit.record_session(make_session())

    pdf = audit.export_session(session_id, "pdf")

    assert pdf.startswith(b"%PDF")
    text = _pdf_text(pdf)
    assert "µg/g".encode("latin-1") in text
    assert b">=" in text
    assert b"Decision support, not diagnosis" in text
    assert b"Synthetic patient" in text


def test_latin1_mapping() -> None:
    mapped = to_latin1_safe("≥ ≤ ✓ ✕ ◐ ⊘ → · µ 你")
    assert mapped == ">= <= OK x partial n/a -> · µ ?"
    mapped.encode("latin-1")
    assert to_latin1_safe(HEADER) == HEADER


def test_unknown_session_raises(audit: AuditService) -> None:
    with pytest.raises(SessionNotFound):
        audit.get_session("s-missing")
    with pytest.raises(SessionNotFound):
        audit.export_session("s-missing", "pdf")


def test_pdf_failure_raises_export_failed(
    audit: AuditService, monkeypatch: pytest.MonkeyPatch
) -> None:
    session_id = audit.record_session(make_session())

    def _broken(self: PdfExporter, detail: object) -> bytes:
        raise RuntimeError("renderer crashed")

    monkeypatch.setattr(PdfExporter, "_render", _broken)
    with pytest.raises(ExportFailed, match="RuntimeError"):
        audit.export_session(session_id, "pdf")
