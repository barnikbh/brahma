"""The follow-up turn: chat text after a walk is read as treatment history and answered
from the graph's history-conditioned edges, every line through the guard."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from brahma.agent.engine import NO_GROUNDED_ANSWER, WalkEngine
from brahma.agent.models import TherapyItem, WalkEvent
from brahma.agent.views import history_note, merge_history, resolve_history
from brahma.cases import Case, CaseService
from brahma.knowledge import KnowledgeService, PackVersionRef
from brahma.platform.audit import AuditService
from tests.agent.conftest import (
    DEMO_TEXT,
    TimeoutAdapter,
    collect,
    of_type,
    recorded,
    walk_through,
)

IBD = PackVersionRef(pack="IBD", number="1.2")
FOLLOW_TEXT = "Remicade failed. steroids work. Suggest alternate treatment plan"
REFRACTORY_TEXT = "Infliximab stopped working and steroids did not work"


def _follow_up(engine: WalkEngine, case_id: str, text: str = FOLLOW_TEXT) -> list[WalkEvent]:
    return collect(engine, case_id, mode="follow_up", text=text)


def _cited(events: list[WalkEvent], section_id: str) -> set[str]:
    lines = of_type(events, "line")
    return {n for line in lines if line["sectionId"] == section_id for n in line["nodeIds"]}


def test_after_anti_tnf_failure_the_follow_up_suggests_a_class_switch(
    engine: WalkEngine,
    demo_case: Case,
    cases: CaseService,
    audit: AuditService,
    audit_rows: Callable[[str], list[dict[str, Any]]],
) -> None:
    walk_through(engine, demo_case.case_id)
    events = _follow_up(engine, demo_case.case_id)
    kinds = [e.type for e in events]
    assert kinds[0] == "progress" and kinds[1] == "history" and kinds[-1] == "done"
    assert "form" not in kinds and "paused" not in kinds
    note = of_type(events, "history")[0]
    assert note["text"] == (
        "Noted treatment history: infliximab — no response; corticosteroid — responded."
    )
    assert [t["drug"] for t in note["therapies"]] == ["infliximab", "corticosteroid"]
    done = of_type(events, "done")[0]
    assert done["outcome"] == "answered" and done["followUp"] is True
    assert done["counts"]["ungrounded"] == 0
    assert done["counts"]["cited"] == len(of_type(events, "line")) > 0
    sections = [s["sectionId"] for s in of_type(events, "section_done")]
    assert sections == ["treatment", "monitor", "watch_outs"]
    assert _cited(events, "treatment") == {"IBD-N46", "IBD-N54", "IBD-N57", "IBD-N58"}
    assert "IBD-N102" in _cited(events, "watch_outs")  # steroids only as a bridge
    assert "IBD-N99" not in _cited(events, "watch_outs")
    texts = " ".join(line["text"] for line in of_type(events, "line"))
    assert "Ustekinumab" in texts

    nodes = {n["nodeId"]: n for n in of_type(events, "map_update")[0]["nodes"]}
    assert nodes["IBD-N46"]["status"] == "entry"
    assert nodes["IBD-N53"]["status"] == "tried"
    assert nodes["IBD-N53"]["result"] == {"response": "failed"}
    assert nodes["IBD-N51"]["result"] == {"response": "responded"}
    assert nodes["IBD-N41"]["status"] == "used"

    history = [r for r in audit_rows(demo_case.case_id) if r["kind"] == "treatment_history"]
    assert len(history) == 1 and history[0]["walkId"] == done["walkId"]
    record = audit.get_session(done["sessionId"]).record
    assert record.inputs.text == FOLLOW_TEXT
    assert [h["drug"] for h in record.inputs.history] == ["infliximab", "corticosteroid"]
    assert record.outcome == "answered"
    assert "UC after anti-TNF failure" in record.answer.summary
    messages = cases.list_messages(demo_case.case_id)
    assert messages[-1].kind == "pathway" and messages[-1].body["history"]
    confirmations = [m for m in messages if m.author == "brahma" and m.kind == "text"]
    assert confirmations[-1].body["text"] == note["text"]
    assert cases.get_case(demo_case.case_id).status == "answered"
    assert engine.can_follow_up(engine.repo.latest_for_case(demo_case.case_id))


def test_steroid_refractory_history_escalates_to_a_surgical_review(
    engine: WalkEngine, demo_case: Case
) -> None:
    walk_through(engine, demo_case.case_id)
    events = _follow_up(engine, demo_case.case_id, REFRACTORY_TEXT)
    assert of_type(events, "history")[0]["text"] == (
        "Noted treatment history: infliximab — lost response; corticosteroid — no response."
    )
    done = of_type(events, "done")[0]
    assert done["outcome"] == "answered" and done["counts"]["ungrounded"] == 0
    watch = _cited(events, "watch_outs")
    assert "IBD-N99" in watch and "IBD-N102" not in watch


def test_brand_names_map_to_the_pack_drug_and_unknown_drugs_are_ignored(
    knowledge: KnowledgeService,
) -> None:
    items = [
        TherapyItem(drug="Remicade", response="failed"),
        TherapyItem(drug="Stelara", response="intolerant"),
        TherapyItem(drug="steroids", response="responded"),
        TherapyItem(drug="Humira", response="failed"),
        TherapyItem(drug="infliximab", response="lost_response"),
    ]
    known, ignored = resolve_history(knowledge, IBD, items)
    assert [(h["drug"], h["response"]) for h in known] == [
        ("infliximab", "lost_response"),  # a later item for the same drug wins
        ("ustekinumab", "intolerant"),
        ("corticosteroid", "responded"),
    ]
    assert known[0]["nodeIds"] == ["IBD-N53"]
    assert set(known[2]["nodeIds"]) == {"IBD-N51", "IBD-N52", "IBD-N55"}
    assert ignored == ["Humira"]
    note = history_note(known, ["Humira", "made-up drug"], "Humira failed, so did Remicade")
    assert "Not in the knowledge pack, so not used: Humira." in note
    assert note.endswith("1 other medicine(s) not in the knowledge pack were not used.")
    assert history_note([], [], "x").startswith("No treatment history")
    merged = merge_history(known[:1], [{"drug": "Infliximab", "response": "failed"}])
    assert merged == [{"drug": "Infliximab", "response": "failed"}]


def test_an_unknown_drug_gives_no_grounded_answer_and_keeps_the_answer(
    engine: WalkEngine, demo_case: Case, cases: CaseService
) -> None:
    walk_through(engine, demo_case.case_id)
    events = _follow_up(engine, demo_case.case_id, "Humira failed last year")
    note = of_type(events, "history")[0]
    assert note["therapies"] == []
    assert "1 other medicine(s) not in the knowledge pack" in note["text"]
    done = of_type(events, "done")[0]
    assert (done["outcome"], done["message"]) == ("out_of_knowledge", NO_GROUNDED_ANSWER)
    assert not of_type(events, "line")
    assert cases.get_case(demo_case.case_id).status == "answered"
    assert done["followUp"] is True  # the doctor can still add history


def test_history_with_no_graph_path_gives_no_grounded_answer(
    engine: WalkEngine, demo_case: Case
) -> None:
    walk_through(engine, demo_case.case_id)
    events = _follow_up(engine, demo_case.case_id, "mesalamine failed before")
    assert of_type(events, "history")[0]["therapies"][0]["drug"] == "mesalamine"
    done = of_type(events, "done")[0]
    assert done["outcome"] == "out_of_knowledge" and not of_type(events, "line")
    # A second follow-up after a no-answer follow-up still works.
    again = _follow_up(engine, demo_case.case_id)
    assert of_type(again, "done")[0]["outcome"] == "answered"


def test_every_follow_up_line_goes_through_the_guard(
    make_engine: Callable[..., WalkEngine],
    demo_case: Case,
    audit_rows: Callable[[str], list[dict[str, Any]]],
) -> None:
    engine = make_engine("follow_up_bad")
    walk_through(engine, demo_case.case_id)
    events = _follow_up(engine, demo_case.case_id)
    shown = [line["text"] for line in of_type(events, "line") if line["sectionId"] == "treatment"]
    assert shown == ["Start here: after anti-TNF failure, change to another drug class (Tier 3)."]
    done = of_type(events, "done")[0]
    assert done["counts"]["ungrounded"] == 2
    rejected = [r for r in audit_rows(demo_case.case_id) if r["kind"] == "line_rejected"]
    assert {tuple(r["citedNodeIds"]) for r in rejected} == {("IBD-N57",), ("IBD-N51",)}


def test_a_follow_up_needs_an_ended_walk_and_text(engine: WalkEngine, demo_case: Case) -> None:
    error = of_type(_follow_up(engine, demo_case.case_id), "error")[0]
    assert error["code"] == "walk_not_resumable"
    collect(engine, demo_case.case_id, mode="start", text=DEMO_TEXT)
    paused = of_type(_follow_up(engine, demo_case.case_id), "error")[0]
    assert paused["code"] == "walk_not_resumable"  # while paused, text is queued instead
    blank = of_type(_follow_up(engine, demo_case.case_id, "  "), "error")[0]
    assert blank["code"] == "invalid_request"


def test_a_failed_history_read_is_retried_with_continue(
    make_engine: Callable[..., WalkEngine], demo_case: Case
) -> None:
    adapter = TimeoutAdapter(recorded(), "Remicade failed", times=3)
    engine = make_engine(adapter=adapter)
    walk_through(engine, demo_case.case_id)
    failed = _follow_up(engine, demo_case.case_id)
    error = of_type(failed, "error")[0]
    assert error["retryable"] is True and error["walkId"]
    retried = collect(engine, demo_case.case_id, mode="continue", walkId=error["walkId"])
    assert of_type(retried, "history") and of_type(retried, "done")[0]["outcome"] == "answered"
