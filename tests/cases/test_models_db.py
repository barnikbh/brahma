"""Models and database (plan step 4): honesty validator, patient change limits, schema."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from pydantic import ValidationError

from brahma.cases import NOT_CHECKED_MESSAGE, MessageIn, PatientChange, SafetyResult, cs_connect
from brahma.cases.db import ensure_cs_schema

CS_TABLES = {
    "cs_patient",
    "cs_case",
    "cs_message",
    "cs_form_draft",
    "cs_finding",
    "cs_tab_lock",
    "cs_treatment_edit",
}


def _tables(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    return {r[0] for r in rows if r[0].startswith("cs_")}


def test_ok_safety_result_without_a_node_is_refused() -> None:
    with pytest.raises(ValidationError, match="must cite a node"):
        SafetyResult(check="allergy", status="ok", node_ids=[], message="fine", drug_node_id="X")


def test_conflict_needs_a_node_but_not_checked_does_not() -> None:
    with pytest.raises(ValidationError):
        SafetyResult(check="pregnancy", status="conflict", message="x", drug_node_id="X")
    result = SafetyResult(
        check="interaction", status="not_checked", message=NOT_CHECKED_MESSAGE, drug_node_id="X"
    )
    assert result.node_ids == []
    assert result.model_dump(by_alias=True)["nodeIds"] == []


def test_patient_change_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        PatientChange.model_validate({"syntheticName": "Someone else"})
    with pytest.raises(ValidationError):
        PatientChange.model_validate({"nhsNumber": "123"})


@pytest.mark.parametrize("weight", [500, 0, -1])
def test_patient_change_rejects_weight_out_of_range(weight: float) -> None:
    with pytest.raises(ValidationError):
        PatientChange.model_validate({"weightKg": weight})
    assert PatientChange.model_validate({"weightKg": 62}).weight_kg == 62


def test_form_message_needs_a_form_kind() -> None:
    with pytest.raises(ValidationError):
        MessageIn(author="brahma", kind="form")
    with pytest.raises(ValidationError):
        MessageIn(author="doctor", kind="text", form_kind="weight")
    assert MessageIn(author="brahma", kind="form", form_kind="weight").form_kind == "weight"


def test_tables_are_created_idempotently(tmp_db: Path) -> None:
    first = cs_connect(tmp_db)
    try:
        assert _tables(first) == CS_TABLES
        ensure_cs_schema(first)
        second = cs_connect(tmp_db)
        assert _tables(second) == CS_TABLES
        assert second.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert {"pf_audit_entry", "pf_profile"} <= {
            r[0] for r in second.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        second.close()
    finally:
        first.close()


def test_messages_and_edits_are_append_only(conn: sqlite3.Connection) -> None:
    conn.execute("INSERT INTO cs_patient VALUES ('pt-1', '{}', 't')")
    conn.execute(
        "INSERT INTO cs_case VALUES ('BR-000001', 'pt-1', 'p-maya', NULL, NULL, 'clinic', NULL, "
        "'new', 1, 't', 't')"
    )
    conn.execute(
        "INSERT INTO cs_message VALUES ('m-1', 'BR-000001', 'brahma', 'form', '{}', 'weight', "
        "'open', 't')"
    )
    conn.execute(
        "INSERT INTO cs_treatment_edit VALUES ('te-1', 'BR-000001', 'IBD-N53', '{}', '{}', "
        "'p-maya', 't')"
    )
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        conn.execute("DELETE FROM cs_message WHERE message_id = 'm-1'")
    with pytest.raises(sqlite3.IntegrityError, match="open to submitted"):
        conn.execute("UPDATE cs_message SET body_json = '{\"x\":1}' WHERE message_id = 'm-1'")
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        conn.execute("UPDATE cs_treatment_edit SET node_id = 'IBD-N50'")
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        conn.execute("DELETE FROM cs_treatment_edit")
    conn.execute("UPDATE cs_message SET form_state = 'submitted' WHERE message_id = 'm-1'")
    conn.execute("INSERT INTO cs_patient VALUES ('pt-2', '{}', 't')")
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        conn.execute(
            "INSERT INTO cs_case VALUES ('BR-000002', 'pt-2', 'p-maya', NULL, NULL, "
            "'benchmark', NULL, 'new', 1, 't', 't')"
        )
