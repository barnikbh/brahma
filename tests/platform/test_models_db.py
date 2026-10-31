"""Models and database: append-only triggers, self-repair and field validation (NFR7.1, NFR7.2)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from brahma.platform.audit.models import SessionRecordIn
from brahma.platform.base import MAX_PAYLOAD_BYTES
from brahma.platform.db import pf_connect, transaction
from brahma.platform.errors import AuditImmutable
from brahma.platform.models.config import ProviderConfig
from brahma.platform.models.schemas import ModelRequest
from tests.platform.factories import make_entry, make_session

_ROWS = {
    "pf_audit_entry": (
        "INSERT INTO pf_audit_entry (entry_id, kind, profile_id, payload_json, created_at) "
        "VALUES ('e1', 'sign_in', 'p-maya', '{}', '2026-10-30T00:00:00')"
    ),
    "pf_session_record": (
        "INSERT INTO pf_session_record (session_id, case_id, walk_id, profile_id, pack_version, "
        "provider, model, outcome, label, search_text, body_json, created_at) VALUES ('e1', "
        "'c', 'w', 'p-maya', 'IBD 1.3', 'recorded', 'recorded', 'answered', 'l', 's', '{}', 't')"
    ),
    "pf_model_call_log": (
        "INSERT INTO pf_model_call_log (call_id, provider, model, purpose, latency_ms, "
        "attempts, created_at) VALUES ('e1', 'recorded', 'recorded', 'extract', 5, 1, 't')"
    ),
}
_KEY_COLUMN = {
    "pf_audit_entry": "entry_id",
    "pf_session_record": "session_id",
    "pf_model_call_log": "call_id",
}


def _seed_row(conn: sqlite3.Connection, table: str) -> None:
    conn.execute(
        "INSERT INTO pf_profile (profile_id, display_name, role, listed) "
        "VALUES ('p-maya', 'Dr. Maya (demo)', 'doctor', 1)"
    )
    conn.execute(_ROWS[table])


@pytest.mark.parametrize("table", sorted(_ROWS))
def test_update_is_refused_on_each_append_only_table(conn: sqlite3.Connection, table: str) -> None:
    _seed_row(conn, table)
    key = _KEY_COLUMN[table]

    with pytest.raises(AuditImmutable), transaction(conn):
        conn.execute(f"UPDATE {table} SET created_at = 'changed' WHERE {key} = 'e1'")

    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        conn.execute(f"UPDATE {table} SET created_at = 'changed'")
    row = conn.execute(f"SELECT created_at FROM {table}").fetchone()
    assert row["created_at"] != "changed"


@pytest.mark.parametrize("table", sorted(_ROWS))
def test_delete_is_refused_on_each_append_only_table(conn: sqlite3.Connection, table: str) -> None:
    _seed_row(conn, table)

    with pytest.raises(AuditImmutable), transaction(conn):
        conn.execute(f"DELETE FROM {table}")

    assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 1


def test_dropped_trigger_is_restored_on_reopen(tmp_db: Path) -> None:
    first = pf_connect(tmp_db)
    _seed_row(first, "pf_audit_entry")
    first.execute("DROP TRIGGER pf_audit_entry_no_delete")
    first.execute("DELETE FROM pf_audit_entry")  # the gap a dropped trigger leaves
    first.execute(_ROWS["pf_audit_entry"])
    first.close()

    reopened = pf_connect(tmp_db)
    try:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            reopened.execute("DELETE FROM pf_audit_entry")
    finally:
        reopened.close()


def test_connection_uses_wal_and_foreign_keys(conn: sqlite3.Connection) -> None:
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(_ROWS["pf_audit_entry"])  # unknown profile: foreign key refuses it


def test_entry_without_profile_is_refused() -> None:
    with pytest.raises(ValidationError, match="profileId"):
        make_entry(profileId=None)
    with pytest.raises(ValidationError):
        make_entry(profileId="")


def test_session_without_model_is_refused() -> None:
    valid = make_session().model_dump(by_alias=True)
    del valid["model"]
    with pytest.raises(ValidationError, match="model"):
        SessionRecordIn.model_validate(valid)
    with pytest.raises(ValidationError):
        make_session(provider="")


def test_payload_over_256_kb_is_refused() -> None:
    assert make_entry(payload={"blob": "x" * (MAX_PAYLOAD_BYTES - 100)})
    with pytest.raises(ValidationError, match="256 KB"):
        make_entry(payload={"blob": "x" * MAX_PAYLOAD_BYTES})
    with pytest.raises(ValidationError, match="256 KB"):
        make_session(inputs={"text": "x" * MAX_PAYLOAD_BYTES, "findings": []})


def test_secret_key_never_shows_in_repr_or_dump() -> None:
    config = ProviderConfig(
        provider="meta",
        model="Llama-4-Maverick",
        api_key_env="META_API_KEY",
        api_key=SecretStr("fake-key-for-tests-0001"),
    )
    assert "fake-key-for-tests-0001" not in repr(config)
    assert "fake-key-for-tests-0001" not in str(config.model_dump())
    assert "fake-key-for-tests-0001" not in config.model_dump_json()


def test_model_request_refuses_bad_messages() -> None:
    with pytest.raises(ValidationError):
        ModelRequest(purpose="extract", messages=[{"role": "robot", "content": "x"}], max_tokens=5)
    with pytest.raises(ValidationError):
        ModelRequest(purpose="extract", messages=[], max_tokens=5)
