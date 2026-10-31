"""The walk engine end to end on recorded replies (plan Step 11; US3.1-US3.6, US7.1)."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from brahma.agent.engine import WalkEngine
from brahma.agent.logging import ALLOWED_FIELDS
from brahma.agent.models import DISCLAIMER, SECTION_ORDER
from brahma.cases import Case, CaseService, FindingIn
from brahma.knowledge import ChangeSet, KnowledgeService, PackVersionRef
from brahma.platform.audit import AuditService
from tests.agent.conftest import (
    DEMO_RESULTS,
    DEMO_TEXT,
    DOCTOR,
    FIRST_RESULTS,
    HEADACHE_TEXT,
    TimeoutAdapter,
    collect,
    confirmed_findings,
    of_type,
    recorded,
    walk_through,
)

IBD_LIVE = PackVersionRef(pack="IBD", number="1.1")


def _lines(events: list[Any]) -> list[dict[str, Any]]:
    return of_type(events, "line")


def test_start_posts_a_confirm_findings_form_and_pauses(
    engine: WalkEngine, demo_case: Case
) -> None:
    events = collect(engine, demo_case.case_id, mode="start", text=DEMO_TEXT)
    assert [e.type for e in events] == ["progress", "form", "paused"]
    assert events[0].payload == {"step": "reading_findings"}
    form = events[1].payload
    assert form["kind"] == "confirm-findings"
    names = {f["name"]: f for f in form["fields"]}
    assert set(names) == {"age", "bloody stool", "Hb", "calprotectin"}
    assert names["bloody stool"]["duration"] == "6 months"
    assert (names["Hb"]["value"], names["Hb"]["unit"]) == (10.2, "g/dL")
    assert events[2].payload["waitingFor"] == form["messageId"]


def test_demo_walk_is_fully_grounded_in_fr4_6_order(
    engine: WalkEngine, demo_case: Case, cases: CaseService
) -> None:
    events = walk_through(engine, demo_case.case_id)
    forms = of_type(events, "form")
    assert [f["kind"] for f in forms] == ["confirm-findings", "needs-data", "needs-data"]
    assert [f["name"] for f in forms[1]["fields"]] == ["IBD-N20", "IBD-N21"]
    done = of_type(events, "done")[0]
    assert done["outcome"] == "answered"
    assert done["counts"]["ungrounded"] == 0
    assert done["counts"]["cited"] == len(_lines(events)) > 0
    assert (done["packVersion"], done["provider"], done["disclaimer"]) == (
        "IBD 1.1",
        "recorded",
        DISCLAIMER,
    )
    order = [s["sectionId"] for s in of_type(events, "section_done")]
    assert order == [*SECTION_ORDER, "why"]
    assert all(line["nodeIds"] for line in _lines(events))
    subtype = {
        n for line in _lines(events) if line["sectionId"] == "subtype" for n in line["nodeIds"]
    }
    assert subtype == {"IBD-N32", "IBD-N34"}  # ulcerative colitis, pancolitis, severe
    assert cases.get_case(demo_case.case_id).pinned_pack_version == IBD_LIVE
    walk = engine.repo.get(done["walkId"])
    assert walk is not None
    entry = [n for n in walk.map["nodes"] if n["status"] == "entry"] if walk.map else []
    assert [n["nodeId"] for n in entry] == ["IBD-N41"]  # Tier 2 entry


def test_wrong_citation_is_never_shown_and_is_audited(
    make_engine: Callable[..., WalkEngine],
    demo_case: Case,
    audit_rows: Callable[[str], list[dict[str, Any]]],
) -> None:
    engine = make_engine("wrong_dose")
    events = walk_through(engine, demo_case.case_id)
    texts = [line["text"] for line in _lines(events)]
    assert not any("120 mg" in t for t in texts)
    assert any(t.startswith("Hydrocortisone 100 mg") for t in texts)
    assert of_type(events, "done")[0]["counts"]["ungrounded"] == 1
    rejected = [r for r in audit_rows(demo_case.case_id) if r["kind"] == "line_rejected"]
    assert len(rejected) == 1
    assert rejected[0]["citedNodeIds"] == ["IBD-N52"]
    reasons = {(f["claim"]["kind"], f["reason"]) for f in rejected[0]["failures"]}
    assert ("dose", "value_differs") in reasons


def test_timeout_mid_stream_then_retry_sends_no_line_twice(
    make_engine: Callable[..., WalkEngine], demo_case: Case
) -> None:
    flaky = TimeoutAdapter(recorded("demo"), '<section id="treatment"', times=3)
    engine = make_engine(adapter=flaky)
    first = walk_through(engine, demo_case.case_id)
    error = of_type(first, "error")[0]
    assert (error["code"], error["retryable"]) == ("model_timeout", True)
    assert "Retry" in error["message"]
    walk = engine.repo.get(error["walkId"])
    assert walk is not None and walk.status == "error"
    assert walk.last_section_done == SECTION_ORDER.index("subtype")
    retry = collect(engine, demo_case.case_id, mode="continue", walkId=error["walkId"])
    sent_first = [(x["sectionId"], x["text"]) for x in _lines(first)]
    sent_retry = [(x["sectionId"], x["text"]) for x in _lines(retry)]
    assert not set(sent_first) & set(sent_retry)
    assert {s for s, _ in sent_retry} >= {"treatment", "monitor", "why"}
    assert of_type(retry, "done")[0]["counts"]["cited"] == len(sent_first) + len(sent_retry)


def test_explore_keeps_main_sections_and_stop_is_audited(
    engine: WalkEngine,
    demo_case: Case,
    audit_rows: Callable[[str], list[dict[str, Any]]],
) -> None:
    done = of_type(walk_through(engine, demo_case.case_id), "done")[0]
    before = engine.repo.get(done["walkId"])
    explored = collect(
        engine, demo_case.case_id, mode="explore", walkId=done["walkId"], branchNodeId="IBD-N13"
    )
    lane_lines = _lines(explored)
    assert lane_lines and all(line["sectionId"] == "explore" for line in lane_lines)
    lane_id = lane_lines[0]["laneId"]
    assert of_type(explored, "map_update")[0]["nodes"][0]["status"] == "exploring"
    after = engine.repo.get(done["walkId"])
    assert before is not None and after is not None and after.sections == before.sections
    data = engine.map_data(demo_case.case_id)
    assert data is not None and [lane.lane_id for lane in data.explore_lanes] == [lane_id]
    stopped = collect(
        engine,
        demo_case.case_id,
        mode="stop_explore",
        walkId=done["walkId"],
        branchNodeId="IBD-N13",
    )
    assert of_type(stopped, "lane_closed")[0]["laneId"] == lane_id
    kinds = [r["kind"] for r in audit_rows(demo_case.case_id)]
    assert kinds.count("explore") == 1 and kinds.count("explored_not_acted") == 1
    again = collect(
        engine,
        demo_case.case_id,
        mode="stop_explore",
        walkId=done["walkId"],
        branchNodeId="IBD-N13",
    )
    assert of_type(again, "error")[0]["code"] == "explore_invalid"


def test_rewalk_on_a_newer_version_records_both(
    engine: WalkEngine,
    demo_case: Case,
    knowledge: KnowledgeService,
    cases: CaseService,
    audit: AuditService,
) -> None:
    walk_through(engine, demo_case.case_id)
    node = knowledge.get_node(IBD_LIVE, "IBD-N60").model_copy(update={"pack_version": None})
    changed = node.model_copy(update={"label": "Diet in ulcerative colitis (reviewed)"})
    knowledge.create_version(
        "IBD", IBD_LIVE, ChangeSet(update_nodes=[changed], change_summary="Label review"), DOCTOR
    )
    events = collect(engine, demo_case.case_id, mode="rewalk")
    done = of_type(events, "done")[0]
    assert (done["packVersion"], done["previousPackVersion"]) == ("IBD 1.2", "IBD 1.1")
    assert done["counts"]["ungrounded"] == 0
    assert cases.get_case(demo_case.case_id).pinned_pack_version == PackVersionRef(
        pack="IBD", number="1.2"
    )
    record = audit.get_session(done["sessionId"]).record
    assert record.pack_version == "IBD 1.2"
    assert "was IBD 1.1" in record.answer.summary


def test_session_record_holds_the_audit_fields(
    engine: WalkEngine, demo_case: Case, audit: AuditService
) -> None:
    done = of_type(walk_through(engine, demo_case.case_id), "done")[0]
    record = audit.get_session(done["sessionId"]).record
    assert (record.profile_id, record.pack_version, record.provider, record.model) == (
        DOCTOR,
        "IBD 1.1",
        "recorded",
        "recorded",
    )
    assert record.inputs.text == DEMO_TEXT
    assert {f["name"] for f in record.inputs.findings} >= {"Hb", "calprotectin"}
    assert record.path_node_ids[:3] == ["IBD-N1", "IBD-N3", "IBD-N5"]
    assert "IBD-N41" in record.path_node_ids
    assert [s["sectionId"] for s in record.answer.sections][:2] == ["findings", "diagnosis"]
    assert "IBD-S2" in record.sources
    assert record.explanation and all(line["nodeIds"] for line in record.explanation)
    assert record.outcome == "answered"


def test_log_has_only_allowed_fields_and_no_text(
    engine: WalkEngine, demo_case: Case, log_path: Path
) -> None:
    walk_through(engine, demo_case.case_id)
    content = log_path.read_text(encoding="utf-8")
    for fragment in ("bloody stool", "34-year-old", "Hydrocortisone", "calprotectin"):
        assert fragment.lower() not in content.lower()
    entries = [json.loads(line) for line in content.splitlines()]
    assert {e["event"] for e in entries} >= {"walk_start", "section_done", "walk_done"}
    assert all(set(e) <= ALLOWED_FIELDS | {"at"} for e in entries)


def test_run_walk_answers_forms_from_the_given_results(engine: WalkEngine, demo_case: Case) -> None:
    findings = [
        FindingIn(kind="symptom", name="bloody stool", duration="6 months"),
        FindingIn(kind="metric", name="Hb", value=10.2, unit="g/dL"),
        FindingIn(kind="metric", name="calprotectin", value=850, unit="µg/g"),
    ]
    answers = {**DEMO_RESULTS[0], "disease extent": "E3", "truelove and witts severity": "severe"}
    result = engine.run_walk(demo_case.case_id, findings, answers)
    assert result.outcome == "answered"
    assert result.counts.ungrounded == 0 and result.counts.cited > 0
    assert result.pack_version == "IBD 1.1"
    assert "IBD-N34" in result.path_node_ids


def test_out_of_knowledge_gives_no_grounded_answer_without_a_model_call(
    engine: WalkEngine, demo_case: Case, conn: sqlite3.Connection
) -> None:
    events = walk_through(engine, demo_case.case_id, text=HEADACHE_TEXT, results=())
    done = of_type(events, "done")[0]
    assert done["outcome"] == "out_of_knowledge"
    assert done["message"] == "No grounded answer"
    assert "suggest_branch" in done["offers"]
    assert _lines(events) == []
    purposes = [r["purpose"] for r in conn.execute("SELECT purpose FROM pf_model_call_log")]
    assert purposes == ["extract"]


def test_partial_results_walk_as_far_as_the_data_allows(
    engine: WalkEngine, demo_case: Case
) -> None:
    events = walk_through(
        engine, demo_case.case_id, results=({"IBD-N21": "ulcerative colitis"}, {"IBD-N22": "E3"})
    )
    done = of_type(events, "done")[0]
    assert done["outcome"] == "needs_data"
    walk = engine.repo.get(done["walkId"])
    assert walk is not None and walk.map is not None
    status = {n["nodeId"]: n["status"] for n in walk.map["nodes"]}
    assert status["IBD-N20"] == status["IBD-N23"] == "test_needed"
    assert status["IBD-N32"] == "used"
    assert "IBD-N41" not in status  # no treatment without the severity
    assert not [x for x in _lines(events) if x["sectionId"] == "treatment"]


def test_invalid_findings_keep_the_form_open(engine: WalkEngine, demo_case: Case) -> None:
    start = collect(engine, demo_case.case_id, mode="start", text=DEMO_TEXT)
    form = of_type(start, "form")[0]
    findings = confirmed_findings(form)
    findings[2] = {**findings[2], "value": "not a number"}
    events = collect(
        engine,
        demo_case.case_id,
        mode="continue",
        walkId=form["walkId"],
        formMessageId=form["messageId"],
        formValues={"findings": findings},
    )
    assert of_type(events, "error")[0]["code"] == "findings_not_ready"
    walk = engine.repo.get(form["walkId"])
    assert walk is not None and (walk.status, walk.waiting_for) == ("paused", form["messageId"])


def test_free_text_during_a_walk_offers_review_and_rewalk(
    engine: WalkEngine, demo_case: Case, cases: CaseService
) -> None:
    from brahma.cases import MessageIn

    start = collect(engine, demo_case.case_id, mode="start", text=DEMO_TEXT)
    message_id = cases.append_message(
        demo_case.case_id, MessageIn(author="doctor", kind="text", body={"text": "joint pain"})
    )
    assert engine.queue_message(demo_case.case_id, message_id) == []
    form = of_type(start, "form")[0]
    events = collect(
        engine,
        demo_case.case_id,
        mode="continue",
        walkId=form["walkId"],
        formMessageId=form["messageId"],
        formValues={"findings": confirmed_findings(form)},
    )
    needs = of_type(events, "form")[0]
    final = collect(
        engine,
        demo_case.case_id,
        mode="continue",
        walkId=form["walkId"],
        formMessageId=needs["messageId"],
        formValues=FIRST_RESULTS,
    )
    second = of_type(final, "form")[0]
    done_events = collect(
        engine,
        demo_case.case_id,
        mode="continue",
        walkId=form["walkId"],
        formMessageId=second["messageId"],
        formValues=DEMO_RESULTS[1],
    )
    assert "review_findings_and_rewalk" in of_type(done_events, "done")[0]["offers"]
    assert engine.queue_message(demo_case.case_id, message_id) == ["review_findings_and_rewalk"]


def test_a_guard_exception_ends_the_walk_with_guard_failure(
    engine: WalkEngine,
    demo_case: Case,
    knowledge: KnowledgeService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real = knowledge.match_claims

    def broken(*_args: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(knowledge, "match_claims", broken)
    events = walk_through(engine, demo_case.case_id)
    error = of_type(events, "error")[0]
    assert (error["code"], error["retryable"]) == ("guard_failure", True)
    sent = [line["text"] for line in _lines(events)]
    assert len(sent) == 1  # a line with no claims; the next line's check raised
    monkeypatch.setattr(knowledge, "match_claims", real)
    retry = collect(engine, demo_case.case_id, mode="continue", walkId=error["walkId"])
    assert not set(sent) & {line["text"] for line in _lines(retry)}
    done = of_type(retry, "done")[0]
    assert done["counts"]["ungrounded"] == 0  # the failed check is not counted twice


def test_requests_that_cannot_run_end_with_an_error_event(
    engine: WalkEngine, demo_case: Case
) -> None:
    missing = collect(engine, demo_case.case_id, mode="continue", walkId="wk-missing")
    assert of_type(missing, "error")[0]["code"] == "walk_not_found"
    no_text = collect(engine, demo_case.case_id, mode="start", text="  ")
    assert of_type(no_text, "error")[0]["code"] == "invalid_request"
    done = of_type(walk_through(engine, demo_case.case_id), "done")[0]
    finished = collect(engine, demo_case.case_id, mode="continue", walkId=done["walkId"])
    assert of_type(finished, "error")[0]["code"] == "walk_not_resumable"
    not_alt = collect(
        engine, demo_case.case_id, mode="explore", walkId=done["walkId"], branchNodeId="IBD-N11"
    )
    assert of_type(not_alt, "error")[0]["code"] == "explore_invalid"
