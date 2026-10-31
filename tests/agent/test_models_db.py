"""U4 models and the ``ag_`` schema (plan Step 4; entities.md, NFR8.1, NFR8.3)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from pydantic import ValidationError

from brahma.agent.db import ag_connect, ensure_ag_schema
from brahma.agent.models import (
    EmittedLine,
    SectionState,
    Walk,
    WalkEvent,
    WalkRequest,
    version_label,
)
from brahma.cases import CaseService, NewPatient
from brahma.knowledge import PackVersionRef


def _walk(case_id: str) -> Walk:
    return Walk(
        walk_id="wk-1",
        case_id=case_id,
        profile_id="p-maya",
        provider="recorded",
        model="recorded",
        started_at="2026-10-30T10:00:00+00:00",
    )


def test_schema_creation_is_repeatable(tmp_db: Path) -> None:
    conn = ag_connect(tmp_db)
    ensure_ag_schema(conn)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"ag_walk", "ag_explore_lane", "cs_case", "pf_audit_entry"} <= tables
    conn.close()


def test_walk_status_and_case_reference_are_enforced(
    conn: sqlite3.Connection, cases: CaseService
) -> None:
    case = cases.create_case(
        NewPatient(synthetic_name="S (synthetic)", age=30, sex="female"), "p-maya"
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO ag_walk VALUES ('wk-x', ?, 'running', '{}', 'a', 'a')", (case.case_id,)
        )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO ag_walk VALUES ('wk-y', 'BR-NONE', 'paused', '{}', 'a', 'a')")


def test_a_stopped_lane_cannot_change_or_be_deleted(
    conn: sqlite3.Connection, cases: CaseService
) -> None:
    case = cases.create_case(
        NewPatient(synthetic_name="S (synthetic)", age=30, sex="female"), "p-maya"
    )
    conn.execute(
        "INSERT INTO ag_walk VALUES ('wk-1', ?, 'answered', '{}', 'a', 'a')", (case.case_id,)
    )
    conn.execute(
        "INSERT INTO ag_explore_lane VALUES ('ln-1', 'wk-1', 'IBD-N13', 'stopped', '{}', 'a')"
    )
    with pytest.raises(sqlite3.IntegrityError, match="stopped lane"):
        conn.execute("UPDATE ag_explore_lane SET status = 'open' WHERE lane_id = 'ln-1'")
    with pytest.raises(sqlite3.IntegrityError, match="kept"):
        conn.execute("DELETE FROM ag_explore_lane WHERE lane_id = 'ln-1'")


def test_walk_request_refuses_unknown_keys_and_long_text() -> None:
    request = WalkRequest.model_validate({"mode": "continue", "walkId": "wk-1"})
    assert request.walk_id == "wk-1"
    with pytest.raises(ValidationError):
        WalkRequest.model_validate({"mode": "start", "text": "x", "extra": 1})
    with pytest.raises(ValidationError):
        WalkRequest.model_validate({"mode": "start", "text": "x" * 4001})
    with pytest.raises(ValidationError):
        WalkRequest.model_validate({"mode": "jump"})


def test_events_frame_as_sse_and_walks_recount() -> None:
    event = WalkEvent(type="line", payload={"text": "µ ok", "nodeIds": ["IBD-N1"]})
    frame = event.sse()
    assert frame.startswith("event: line\ndata: ") and frame.endswith("\n\n")
    assert json.loads(frame.split("data: ", 1)[1]) == {"text": "µ ok", "nodeIds": ["IBD-N1"]}
    walk = _walk("BR-1")
    walk.path_node_ids = ["IBD-N1", "IBD-N10"]
    line = EmittedLine(section_id="findings", text="t", node_ids=["IBD-N1"])
    walk.replace_section(walk.section("findings"))
    walk.replace_section(SectionState(section_id="findings", lines=[line], rejected=2))
    walk.recount()
    assert walk.counts.model_dump() == {"steps": 2, "cited": 1, "ungrounded": 2}
    assert version_label(PackVersionRef(pack="IBD", number="1.0")) == "IBD 1.0"
    assert version_label(None) is None
