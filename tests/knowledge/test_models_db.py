"""Models and database layer (Step 4): schemas, pragmas, immutability triggers, one-live index."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from brahma.knowledge.db import default_db_path
from brahma.knowledge.models import (
    FIELD_SCHEMAS,
    ChangeSet,
    DrugFields,
    Fact,
    Node,
    PackVersionRef,
    Step,
    parse_version,
)


def _drug_fields() -> dict[str, Any]:
    return {
        "drug": "methylprednisolone",
        "synonyms": [],
        "drugClass": "corticosteroid",
        "route": "intravenous",
        "doseValue": 60,
        "doseUnit": "mg",
        "doseBasis": "absolute",
        "rounding": "not applicable",
        "frequency": "once daily",
        "duration": "until review",
        "contraindications": [],
    }


def _node(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "nodeId": "TST-N1",
        "type": "drug",
        "label": "Drug",
        "content": "A drug.",
        "fields": _drug_fields(),
        "sourceIds": ["TST-S1"],
        "column": "treatment",
    }
    base.update(overrides)
    return base


def _seed(conn: sqlite3.Connection) -> None:
    conn.execute("INSERT INTO kg_pack VALUES ('TST', 'TST', 'Test pack', 'Testing')")
    conn.execute(
        "INSERT INTO kg_pack_version VALUES "
        "('TST@1.0', 'TST', '1.0', 1, 0, 'live', 't', 'system', 'Initial load', NULL)"
    )
    conn.execute("INSERT INTO kg_source VALUES ('TST-S1', 'TST', '{}')")
    conn.execute("INSERT INTO kg_node VALUES ('TST@1.0', 'TST-N1', 'symptom', '{}')")
    conn.execute("INSERT INTO kg_node VALUES ('TST@1.0', 'TST-N2', 'symptom', '{}')")
    conn.execute("INSERT INTO kg_edge VALUES ('TST@1.0', 'TST-E1', 'TST-N1', 'TST-N2', '{}')")


@pytest.fixture
def conn(connect: Callable[..., sqlite3.Connection]) -> sqlite3.Connection:
    connection = connect()
    _seed(connection)
    return connection


def test_drug_requires_every_dose_field() -> None:
    fields = _drug_fields()
    DrugFields.model_validate(fields)
    for key in ("doseValue", "doseUnit", "doseBasis", "frequency", "duration"):
        broken = dict(fields)
        del broken[key]
        with pytest.raises(ValidationError, match=key):
            DrugFields.model_validate(broken)
    assert set(FIELD_SCHEMAS) == set(Node.model_fields["type"].annotation.__args__)  # type: ignore[union-attr]


def test_extra_fields_rejected_on_node_and_field_schema() -> None:
    with pytest.raises(ValidationError, match="patientName"):
        Node.model_validate(_node(patientName="someone"))
    with pytest.raises(ValidationError, match="mrn"):
        DrugFields.model_validate({**_drug_fields(), "mrn": "x"})
    with pytest.raises(ValidationError):
        Node.model_validate(_node(sourceIds=[]))


def test_connection_pragmas_set(tmp_db: Path, connect: Callable[..., sqlite3.Connection]) -> None:
    connection = connect()
    assert connection.isolation_level is None
    assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert connection.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
    assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert default_db_path() == str(tmp_db)


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE kg_pack SET name = 'x'",
        "DELETE FROM kg_pack",
        "UPDATE kg_node SET body_json = '{\"x\": 1}'",
        "DELETE FROM kg_node",
        "UPDATE kg_edge SET body_json = '{\"x\": 1}'",
        "DELETE FROM kg_edge",
        "UPDATE kg_source SET body_json = '{\"x\": 1}'",
        "DELETE FROM kg_source",
        "DELETE FROM kg_pack_version",
        "UPDATE kg_pack_version SET change_summary = 'rewritten'",
    ],
)
def test_update_and_delete_refused(conn: sqlite3.Connection, statement: str) -> None:
    with pytest.raises(sqlite3.IntegrityError, match=r"immutable|only change status"):
        conn.execute(statement)


def test_status_moves_only_from_live_to_superseded(conn: sqlite3.Connection) -> None:
    conn.execute("UPDATE kg_pack_version SET status = 'superseded' WHERE pack_version_id='TST@1.0'")
    with pytest.raises(sqlite3.IntegrityError, match="only change status"):
        conn.execute("UPDATE kg_pack_version SET status = 'live' WHERE pack_version_id='TST@1.0'")


def test_second_live_version_refused_by_index(conn: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
        conn.execute(
            "INSERT INTO kg_pack_version VALUES "
            "('TST@1.1', 'TST', '1.1', 1, 1, 'live', 't', 'system', 'Second', 'TST@1.0')"
        )


def test_self_edge_and_dangling_edge_refused(conn: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO kg_edge VALUES ('TST@1.0', 'TST-E2', 'TST-N1', 'TST-N1', '{}')")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO kg_edge VALUES ('TST@1.0', 'TST-E3', 'TST-N1', 'TST-N9', '{}')")


def test_fact_step_changeset_and_version_validation() -> None:
    fact = Fact.model_validate({"kind": "test", "name": "Hb", "value": 102, "unit": "g/L"})
    assert fact.value == 102
    with pytest.raises(ValidationError):
        Fact.model_validate({"kind": "guess", "name": "Hb"})
    with pytest.raises(ValidationError):
        Fact.model_validate({"kind": "finding", "name": ""})
    with pytest.raises(ValidationError):
        ChangeSet.model_validate({"changeSummary": "   "})
    with pytest.raises(ValidationError):
        ChangeSet.model_validate({"addNodes": []})
    change = ChangeSet.model_validate({"removeNodeIds": ["TST-N1"], "changeSummary": "Drop"})
    assert change.remove_node_ids == ["TST-N1"]
    node = Node.model_validate(_node())
    edge = {"edgeId": "E", "fromNodeId": "A", "toNodeId": "B", "relation": "suggests"}
    with pytest.raises(ValidationError):
        Step.model_validate({"edge": edge, "node": node, "status": "maybe"})
    with pytest.raises(ValidationError):
        PackVersionRef(pack="TST", number="1")
    assert parse_version("1.10") > parse_version("1.9")
    with pytest.raises(ValueError, match=r"major\.minor"):
        parse_version("v1")
