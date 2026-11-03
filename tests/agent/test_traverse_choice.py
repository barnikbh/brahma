"""Recording a drug choice and re-lighting its tier (no model call)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from brahma.agent.engine import WalkEngine
from brahma.agent.errors import TraverseInvalid
from brahma.agent.models import MapData
from brahma.agent.repository import WalkRepository
from brahma.cases import Case
from tests.agent.conftest import DOCTOR, URO_TEXT, collect, walk_through


def _statuses(data: MapData) -> dict[str, str]:
    return {n.node_id: n.status for n in data.nodes}


def test_choice_marks_the_drug_chosen_and_lights_its_tier(
    engine: WalkEngine, demo_case: Case
) -> None:
    walk_through(engine, demo_case.case_id)
    data, notice = engine.traverse_choice(demo_case.case_id, "IBD-N51", DOCTOR)
    statuses = _statuses(data)
    assert statuses["IBD-N51"] == "chosen"
    assert statuses["IBD-N52"] == "option"
    assert statuses["IBD-N70"] == "used"
    assert statuses["IBD-N80"] == "used"
    assert statuses["IBD-N42"] == "planned"
    assert statuses["IBD-N41"] == "entry"
    styles = {e.edge_id: e.style for e in data.edges}
    assert styles["IBD-E30"] == "walked"
    assert styles["IBD-E31"] == "not_taken"
    assert "Hydrocortisone" in notice


def test_choice_is_stored_audited_and_survives_reload(
    engine: WalkEngine,
    demo_case: Case,
    repo: WalkRepository,
    audit_rows: Callable[[str], list[dict[str, Any]]],
) -> None:
    walk_through(engine, demo_case.case_id)
    walk_id = repo.latest_for_case(demo_case.case_id).walk_id
    engine.traverse_choice(demo_case.case_id, "IBD-N51", DOCTOR)
    assert repo.choices_for_walk(walk_id) == {"IBD-N41": "IBD-N51"}
    entries = [r for r in audit_rows(demo_case.case_id) if r["kind"] == "traverse_choice"]
    assert len(entries) == 1
    assert entries[0]["tierId"] == "IBD-N41"
    assert entries[0]["nodeId"] == "IBD-N51"
    assert entries[0]["previousNodeId"] is None
    reloaded = engine.map_data(demo_case.case_id)
    assert reloaded is not None
    assert _statuses(reloaded)["IBD-N51"] == "chosen"


def test_rechoosing_moves_the_highlight_and_keeps_history(
    engine: WalkEngine,
    demo_case: Case,
    repo: WalkRepository,
    audit_rows: Callable[[str], list[dict[str, Any]]],
) -> None:
    walk_through(engine, demo_case.case_id)
    engine.traverse_choice(demo_case.case_id, "IBD-N51", DOCTOR)
    data, _ = engine.traverse_choice(demo_case.case_id, "IBD-N52", DOCTOR)
    statuses = _statuses(data)
    assert statuses["IBD-N51"] == "option"
    assert statuses["IBD-N52"] == "chosen"
    assert statuses["IBD-N70"] == "used"  # same tier downstream stays lit
    walk_id = repo.latest_for_case(demo_case.case_id).walk_id
    assert repo.choices_for_walk(walk_id) == {"IBD-N41": "IBD-N52"}
    entries = [r for r in audit_rows(demo_case.case_id) if r["kind"] == "traverse_choice"]
    assert [e["nodeId"] for e in entries] == ["IBD-N51", "IBD-N52"]
    assert entries[1]["previousNodeId"] == "IBD-N51"


def test_traverse_needs_an_answered_walk_with_the_option_on_its_map(
    engine: WalkEngine, demo_case: Case, uro_case: Case
) -> None:
    with pytest.raises(TraverseInvalid, match="no walk yet"):
        engine.traverse_choice(uro_case.case_id, "IBD-N51", DOCTOR)
    collect(engine, uro_case.case_id, DOCTOR, mode="start", text=URO_TEXT)
    with pytest.raises(TraverseInvalid, match="not answered yet"):
        engine.traverse_choice(uro_case.case_id, "URO-N6", DOCTOR)
    walk_through(engine, demo_case.case_id)
    with pytest.raises(TraverseInvalid, match="not an option"):
        engine.traverse_choice(demo_case.case_id, "IBD-N41", DOCTOR)
    with pytest.raises(TraverseInvalid, match="not an option"):
        engine.traverse_choice(demo_case.case_id, "IBD-N999", DOCTOR)
