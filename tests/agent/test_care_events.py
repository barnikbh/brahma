"""The care loop: events re-light the map from the pack's edges, with no model call."""

from __future__ import annotations

from typing import Any

import pytest

from brahma.agent.engine import WalkEngine
from brahma.agent.errors import TraverseInvalid
from brahma.agent.models import MapData
from brahma.cases import Case
from tests.agent.conftest import DOCTOR, collect, walk_through

FOLLOW = "Remicade failed. steroids work. Suggest alternate treatment plan"


def _statuses(data: MapData) -> dict[str, str]:
    return {n.node_id: n.status for n in data.nodes}


def _to_biologic_options(engine: WalkEngine, case_id: str) -> None:
    walk_through(engine, case_id)
    collect(engine, case_id, mode="follow_up", text=FOLLOW)


def test_choosing_a_biologic_lights_both_screens_to_do_first(
    engine: WalkEngine, demo_case: Case
) -> None:
    _to_biologic_options(engine, demo_case.case_id)
    data, _, _ = engine.traverse_choice(demo_case.case_id, "IBD-N57", DOCTOR)
    statuses = _statuses(data)
    assert statuses["IBD-N110"] == statuses["IBD-N111"] == "todo_first"
    nodes = {n.node_id: n for n in data.nodes}
    assert nodes["IBD-N110"].kind == "test" and nodes["IBD-N57"].kind == "action"
    assert {e.relation for e in data.edges if e.to in ("IBD-N110", "IBD-N111")} == {"requires"}


def test_a_recorded_result_is_for_the_chosen_treatment_and_lights_nothing_new(
    engine: WalkEngine, demo_case: Case
) -> None:
    _to_biologic_options(engine, demo_case.case_id)
    engine.traverse_choice(demo_case.case_id, "IBD-N57", DOCTOR)
    data, lit, _ = engine.record_event(demo_case.case_id, "result", "IBD-N110", "negative", DOCTOR)
    statuses = _statuses(data)
    assert statuses["IBD-N110"] == "done" and statuses["IBD-N111"] == "todo_first"
    assert lit == []
    result = next(n.result for n in data.nodes if n.node_id == "IBD-N110")
    assert result == {"value": "negative"}


def test_a_new_choice_asks_for_the_screens_again(engine: WalkEngine, demo_case: Case) -> None:
    _to_biologic_options(engine, demo_case.case_id)
    engine.traverse_choice(demo_case.case_id, "IBD-N57", DOCTOR)
    engine.record_event(demo_case.case_id, "result", "IBD-N110", "negative", DOCTOR)
    data, _, _ = engine.traverse_choice(demo_case.case_id, "IBD-N54", DOCTOR)
    # The result was recorded for vedolizumab; it does not count for ustekinumab.
    assert _statuses(data)["IBD-N110"] == "todo_first"


def test_a_sign_present_lights_what_follows_it(engine: WalkEngine, demo_case: Case) -> None:
    walk_through(engine, demo_case.case_id)
    engine.traverse_choice(demo_case.case_id, "IBD-N51", DOCTOR)
    data, lit, notice = engine.record_event(demo_case.case_id, "present", "IBD-N90", None, DOCTOR)
    statuses = _statuses(data)
    assert statuses["IBD-N90"] == "present" and statuses["IBD-N96"] == "now"
    assert {i.node_id for i in lit} == {"IBD-N90", "IBD-N96"}
    assert "present" in notice


def test_new_bloody_diarrhoea_brings_the_stool_tests_back_due(
    engine: WalkEngine, demo_case: Case
) -> None:
    walk_through(engine, demo_case.case_id)
    data, _, _ = engine.record_event(demo_case.case_id, "present", "IBD-N94", None, DOCTOR)
    assert _statuses(data)["IBD-N20"] == "due"
    data, _, _ = engine.record_event(demo_case.case_id, "result", "IBD-N20", "negative", DOCTOR)
    assert _statuses(data)["IBD-N20"] == "done"


def test_monitoring_result_is_checked_and_marked_done(engine: WalkEngine, demo_case: Case) -> None:
    walk_through(engine, demo_case.case_id)
    engine.traverse_choice(demo_case.case_id, "IBD-N51", DOCTOR)
    data, _, _ = engine.record_event(demo_case.case_id, "result", "IBD-N71", "30", DOCTOR)
    assert _statuses(data)["IBD-N71"] == "done"
    for kind, node, value in [
        ("result", "IBD-N71", "abc"),
        ("result", "IBD-N71", "-4"),
        ("result", "IBD-N20", "maybe"),
        ("result", "IBD-N90", "1"),
        ("present", "IBD-N51", None),
        ("present", "IBD-N999", None),
    ]:
        with pytest.raises(TraverseInvalid):
            engine.record_event(demo_case.case_id, kind, node, value, DOCTOR)  # type: ignore[arg-type]


def test_events_are_audited_and_replayed_on_the_map(
    engine: WalkEngine, demo_case: Case, audit_rows: Any
) -> None:
    walk_through(engine, demo_case.case_id)
    engine.record_event(demo_case.case_id, "present", "IBD-N94", None, DOCTOR)
    assert [r["kind"] for r in audit_rows(demo_case.case_id)].count("care_event") == 1
    replay = engine.map_data(demo_case.case_id)
    assert replay is not None and _statuses(replay)["IBD-N20"] == "due"


def test_the_event_card_is_written_from_the_lit_nodes_and_guarded(
    engine: WalkEngine, demo_case: Case
) -> None:
    walk_through(engine, demo_case.case_id)
    card = engine.event_card(demo_case.case_id, [])
    assert card == {"lines": [], "rejected": 0}


def test_the_card_for_the_screens_is_cited_and_passes_the_guard(
    engine: WalkEngine, demo_case: Case
) -> None:
    _to_biologic_options(engine, demo_case.case_id)
    engine.traverse_choice(demo_case.case_id, "IBD-N57", DOCTOR)
    card = engine.event_card(demo_case.case_id, ["IBD-N110", "IBD-N111"])
    assert card["rejected"] == 0
    assert [line["nodeIds"] for line in card["lines"]] == [["IBD-N110"], ["IBD-N111"]]
    # A line may only cite the nodes that were lit: nothing else is allowed through.
    assert engine.event_card(demo_case.case_id, ["IBD-N70"]) == {"lines": [], "rejected": 0}


def _review_to_tier_3(engine: WalkEngine, case_id: str) -> None:
    walk_through(engine, case_id)
    collect(engine, case_id, mode="review", branch_node_id="IBD-N81", review_value="60")


def test_trough_level_hangs_off_infliximab_and_lights_only_when_it_is_chosen(
    engine: WalkEngine, demo_case: Case
) -> None:
    _review_to_tier_3(engine, demo_case.case_id)
    data = engine.map_data(demo_case.case_id)
    assert data is not None
    edges = {(e.from_, e.to) for e in data.edges}
    assert ("IBD-N53", "IBD-N72") in edges and ("IBD-N42", "IBD-N72") not in edges
    assert _statuses(data)["IBD-N72"] == "planned"
    data, _, path = engine.traverse_choice(demo_case.case_id, "IBD-N54", DOCTOR)
    assert _statuses(data)["IBD-N72"] == "planned"  # ustekinumab has no trough check here
    assert "IBD-N72" not in [i.node_id for i in path.monitor]
    data, _, path = engine.traverse_choice(demo_case.case_id, "IBD-N53", DOCTOR)
    statuses = _statuses(data)
    assert statuses["IBD-N72"] == "due"
    assert statuses["IBD-N110"] == statuses["IBD-N111"] == "todo_first"
    assert [i.node_id for i in path.monitor] == ["IBD-N72"]
    assert [i.node_id for i in path.requires] == ["IBD-N110", "IBD-N111"]


def test_jak_clot_risk_hangs_off_tofacitinib(engine: WalkEngine, demo_case: Case) -> None:
    _to_biologic_options(engine, demo_case.case_id)
    data = engine.map_data(demo_case.case_id)
    assert data is not None
    assert ("IBD-N58", "IBD-N103") in {(e.from_, e.to) for e in data.edges}
    assert _statuses(data)["IBD-N103"] == "planned"
    data, _, _ = engine.traverse_choice(demo_case.case_id, "IBD-N58", DOCTOR)
    assert _statuses(data)["IBD-N103"] == "watch"


def test_a_new_walk_keeps_the_earlier_steps_as_history(engine: WalkEngine, demo_case: Case) -> None:
    walk_through(engine, demo_case.case_id)
    engine.traverse_choice(demo_case.case_id, "IBD-N51", DOCTOR)
    engine.record_event(demo_case.case_id, "result", "IBD-N71", "55", DOCTOR)
    collect(engine, demo_case.case_id, mode="review", branch_node_id="IBD-N81", review_value="60")
    data = engine.map_data(demo_case.case_id)
    assert data is not None
    statuses = _statuses(data)
    assert statuses["IBD-N42"] == "entry"  # the new step
    assert statuses["IBD-N41"] == "done"  # the tier the patient was on
    assert statuses["IBD-N51"] == "tried"  # the drug chosen then
    assert statuses["IBD-N52"] == "not_taken"  # the option not taken
    assert statuses["IBD-N71"] == "done"  # the monitoring result recorded earlier
    assert next(n.result for n in data.nodes if n.node_id == "IBD-N71") == {"value": "55"}
    assert "IBD-N1" in statuses  # presenting findings stay
    edges = {(e.from_, e.to) for e in data.edges}
    assert ("IBD-N41", "IBD-N51") in edges
    # A later choice on the new walk keeps the history too.
    data, _, _ = engine.traverse_choice(demo_case.case_id, "IBD-N53", DOCTOR)
    assert _statuses(data)["IBD-N41"] == "done" and _statuses(data)["IBD-N53"] == "chosen"


def test_a_result_recorded_before_any_choice_still_counts_as_done(
    engine: WalkEngine, demo_case: Case
) -> None:
    walk_through(engine, demo_case.case_id)
    data, _, _ = engine.record_event(demo_case.case_id, "result", "IBD-N71", "55", DOCTOR)
    assert _statuses(data)["IBD-N71"] == "done"
    collect(engine, demo_case.case_id, mode="review", branch_node_id="IBD-N81", review_value="60")
    data = engine.map_data(demo_case.case_id)
    assert data is not None and _statuses(data)["IBD-N71"] == "done"
    assert _statuses(data)["IBD-N51"] == "not_taken"  # never chosen on this case
