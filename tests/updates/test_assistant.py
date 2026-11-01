"""The update conversation (assistant), browse reads and attribution (Knowledge screen)."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from brahma.knowledge.errors import NodeNotFound, VersionNotFound
from brahma.platform.errors import ModelUnavailable
from brahma.updates import api, browse
from brahma.updates.assistant import MAX_ROUNDS, UpdateAssistant
from brahma.updates.errors import (
    DraftFailed,
    ProposalInvalid,
    ThreadClosed,
    ThreadNotFound,
)
from brahma.updates.service import UpdateService
from tests.updates.conftest import DOCTOR, REVIEWER

URL = "https://guidelines.example.org/synthetic/maintenance"
PAGE = (
    "<html><head><title>Synthetic maintenance note</title></head><body>"
    "<p>This invented page says the second biologic maintenance dose is 100 mg given "
    "under the skin every 8 weeks in this made up test.</p>"
    "<p>A second paragraph about nothing clinical at all.</p></body></html>"
)
ASK = {"action": "ask", "questions": ["Which drug do you mean?", "Which URL?"], "targets": []}


def interpret(*node_ids: str, url: str | None = URL) -> dict[str, Any]:
    targets = [
        {"nodeId": n, "instruction": "update the maintenance dose", "url": url} for n in node_ids
    ]
    return {"action": "draft", "questions": [], "targets": targets, "summary": "Update dose."}


def updated(node_id: str, **draft: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "status": "updated",
        "content": "Ustekinumab is given under the skin as maintenance, dose per the new note.",
        "fields": {"doseValue": 100, "frequency": "every 8 weeks"},
    }
    return {"match": f'"nodeId": "{node_id}"', "reply": {**base, **draft}}


@pytest.fixture
def script(tmp_path: Path) -> Callable[..., Path]:
    """Write ``knowledge_update`` replies: node replies by node ID, then interpretations."""

    def _write(interpretations: list[tuple[str, dict[str, Any]]], *nodes: dict[str, Any]) -> Path:
        folder = tmp_path / "rec" / "knowledge_update"
        folder.mkdir(parents=True, exist_ok=True)
        replies = [
            {"match": n["match"], "text": json.dumps(n["reply"]), "inputTokens": 1} for n in nodes
        ]
        replies += [
            {"match": m, "text": json.dumps(r), "inputTokens": 1} for m, r in interpretations
        ]
        (folder / "default.json").write_text(json.dumps({"replies": replies}), "utf-8")
        return tmp_path / "rec"

    return _write


@pytest.fixture
def serve(http: respx.MockRouter) -> None:
    http.get(URL).mock(
        return_value=httpx.Response(200, text=PAGE, headers={"content-type": "text/html"})
    )


def assistant(make_service: Callable[..., UpdateService], folder: Path) -> UpdateAssistant:
    return UpdateAssistant(make_service(folder))


def test_asks_then_drafts_one_proposal_node_by_node(
    make_service: Callable[..., UpdateService], script: Callable[..., Path], serve: None
) -> None:
    folder = script([("https://", interpret("IBD-N54")), ("doctor:", ASK)], updated("IBD-N54"))
    bot = assistant(make_service, folder)
    first = bot.send(DOCTOR, "Update ustekinumab maintenance dose")
    assert first.status == "open" and first.rounds == 1
    assert "Which drug" in first.messages[-1].text and first.messages[-1].proposal_id is None
    second = bot.send(DOCTOR, f"See {URL}.", first.thread_id)
    assert second.status == "proposed" and second.rounds == 0
    assert [m.role for m in second.messages] == ["doctor", "assistant", "doctor", "assistant"]
    proposal = bot._service.get_proposal(second.messages[-1].proposal_id or "")
    change = proposal.changes[0]
    assert proposal.origin == "drafted" and proposal.proposer_profile_id == DOCTOR
    assert change.before and change.before["fields"]["doseValue"] != 100
    assert change.after["fields"]["doseValue"] == 100
    assert change.source_url == URL and change.source_passage and not change.copy_flag
    assert bot.get_thread(first.thread_id, DOCTOR).messages == second.messages
    assert bot.list_threads(DOCTOR)[0].thread_id == first.thread_id


def test_one_node_needing_clarification_is_listed_while_the_other_is_drafted(
    make_service: Callable[..., UpdateService], script: Callable[..., Path], serve: None
) -> None:
    ask = {"match": '"nodeId": "IBD-N57"', "reply": {"status": "ask", "question": "Which route?"}}
    folder = script([("https://", interpret("IBD-N54", "IBD-N57"))], updated("IBD-N54"), ask)
    thread = assistant(make_service, folder).send(DOCTOR, f"update both from {URL}")
    assert thread.status == "proposed"
    assert "1 node(s): IBD-N54" in thread.messages[-1].text
    assert "Still open: Which route?" in thread.messages[-1].text


def test_unreachable_url_asks_instead_of_drafting(
    make_service: Callable[..., UpdateService],
    script: Callable[..., Path],
    http: respx.MockRouter,
) -> None:
    http.get(URL).mock(return_value=httpx.Response(500))
    folder = script([("https://", interpret("IBD-N54"))], updated("IBD-N54"))
    thread = assistant(make_service, folder).send(DOCTOR, f"update from {URL}")
    assert thread.status == "open" and thread.rounds == 1
    assert "could not read" in thread.messages[-1].text and thread.messages[-1].proposal_id is None


def test_unknown_node_and_missing_url_become_questions(
    make_service: Callable[..., UpdateService], script: Callable[..., Path]
) -> None:
    folder = script([("doctor:", interpret("IBD-N999", "IBD-N54", url=None))])
    thread = assistant(make_service, folder).send(DOCTOR, "update things, no link")
    text = thread.messages[-1].text
    assert "IBD-N999" in text and "Which source URL" in text


def test_a_value_the_page_does_not_state_is_asked_not_invented(
    make_service: Callable[..., UpdateService], script: Callable[..., Path], serve: None
) -> None:
    folder = script(
        [("https://", interpret("IBD-N54"))], updated("IBD-N54", fields={"doseValue": 999})
    )
    thread = assistant(make_service, folder).send(DOCTOR, f"update from {URL}")
    assert thread.status == "open"
    assert "does not clearly state doseValue" in thread.messages[-1].text


def test_unchanged_and_invalid_drafts_do_not_become_proposals(
    make_service: Callable[..., UpdateService], script: Callable[..., Path], serve: None
) -> None:
    folder = script(
        [("https://", interpret("IBD-N54", "IBD-N57", "IBD-N52"))],
        {"match": '"nodeId": "IBD-N54"', "reply": {"status": "unchanged", "note": "Nothing new."}},
        updated("IBD-N57", fields={"doseUnit": 5}),
        updated("IBD-N52", content=None, fields={}),
    )
    thread = assistant(make_service, folder).send(DOCTOR, f"check these from {URL}")
    text = thread.messages[-1].text
    assert thread.status == "open" and "Nothing new." in text


def test_copied_source_text_is_flagged_and_blocks_publishing(
    make_service: Callable[..., UpdateService],
    script: Callable[..., Path],
    http: respx.MockRouter,
) -> None:
    long = " ".join(f"word{i}" for i in range(40))
    page = f"<html><title>t</title><body><p>{long} 100 mg</p></body></html>"
    http.get(URL).mock(
        return_value=httpx.Response(200, text=page, headers={"content-type": "text/html"})
    )
    folder = script(
        [("https://", interpret("IBD-N54"))], updated("IBD-N54", content=long, fields={})
    )
    bot = assistant(make_service, folder)
    thread = bot.send(DOCTOR, f"update from {URL}")
    assert "verbatim" in thread.messages[-1].text
    proposal = bot._service.get_proposal(thread.messages[-1].proposal_id or "")
    assert proposal.copy_flagged_node_ids == ["IBD-N54"]


def test_repeated_messages_without_material_stop_early(
    make_service: Callable[..., UpdateService], script: Callable[..., Path]
) -> None:
    bot = assistant(make_service, script([("doctor:", ASK)]))
    thread = bot.send(DOCTOR, "update something")
    assert thread.status == "open" and thread.rounds == 1
    thread = bot.send(DOCTOR, "still unsure", thread.thread_id)
    last = thread.messages[-1].text
    assert thread.status == "stuck" and "instead of asking again" in last
    assert "Which drug" not in last
    with pytest.raises(ThreadClosed):
        bot.send(DOCTOR, "one more", thread.thread_id)


def test_an_enumerated_non_answer_stops_early(
    make_service: Callable[..., UpdateService], script: Callable[..., Path]
) -> None:
    bot = assistant(make_service, script([("doctor:", ASK)]))
    thread = bot.send(DOCTOR, "create knowledge on lung cancer")
    assert thread.status == "open"
    thread = bot.send(
        DOCTOR, "1. yes new, 2. find your own sources, 3. find it all", thread.thread_id
    )
    assert thread.status == "stuck" and "can't create a new pack" in thread.messages[-1].text


def test_rounds_with_new_material_still_run_to_five(
    make_service: Callable[..., UpdateService], script: Callable[..., Path]
) -> None:
    asked = ("Is this for adults?", "Oral or injected?", "How long a course?", "Any taper wanted?")
    rounds = [
        (f"try node IBD-N5{i}", {"action": "ask", "questions": [question]})
        for i, question in enumerate(asked)
    ]
    # The transcript keeps earlier messages, so the latest round's entry must match first.
    bot = assistant(make_service, script([*reversed(rounds), ("doctor:", ASK)]))
    thread = bot.send(DOCTOR, "update something")
    for i in range(MAX_ROUNDS - 1):
        thread = bot.send(DOCTOR, f"try node IBD-N5{i}", thread.thread_id)
    assert thread.status == "stuck" and "could not work this out" in thread.messages[-1].text


def test_a_number_answer_is_treated_as_progress(
    make_service: Callable[..., UpdateService], script: Callable[..., Path]
) -> None:
    later = {"action": "ask", "questions": ["Is that per kilogram of weight?"]}
    bot = assistant(make_service, script([("doctor: 40", later), ("doctor:", ASK)]))
    thread = bot.send(DOCTOR, "update something")
    thread = bot.send(DOCTOR, "40", thread.thread_id)
    assert thread.status == "open" and thread.rounds == 2


def test_model_failure_stores_nothing_and_inputs_are_validated(
    make_service: Callable[..., UpdateService], tmp_path: Path
) -> None:
    bot = assistant(make_service, tmp_path / "empty")
    with pytest.raises(DraftFailed):
        bot.send(DOCTOR, "update something")
    assert bot.list_threads(DOCTOR) == []
    with pytest.raises(ProposalInvalid):
        bot.send(DOCTOR, "   ")
    with pytest.raises(ProposalInvalid):
        bot.send(DOCTOR, "x" * 4001)


def test_bad_model_output_is_a_draft_failure(
    make_service: Callable[..., UpdateService], script: Callable[..., Path]
) -> None:
    bot = assistant(make_service, script([("doctor:", {"action": "nonsense"})]))
    with pytest.raises(DraftFailed):
        bot.send(DOCTOR, "update something")


# --- source first: read the page, decide add or update, cite it ---------------------------

BAND_URL = "https://guidelines.example.org/synthetic/biologic-dosing"
# Synthetic test page: made-up wording, not taken from any guideline.
BAND_PAGE = (
    "<html><head><title>Synthetic biologic dosing note</title></head><body>"
    "<h2>Dosing</h2><p>This invented note covers a made up first infusion.</p>"
    "<p>55 kg or less: 260 mg IV</p><p>Above 55 kg to 85 kg: 390 mg IV</p>"
    "<p>Above 85 kg: 520 mg IV</p><p>Then 90 mg under the skin every 8 weeks.</p>"
    "<h2>Other</h2><p>Unrelated text about storage of the invented product.</p>"
    "</body></html>"
)
REQUEST = f"update ustekinumab dose ≤55 kg: 260 mg IV; >55 kg to 85 kg: 390 from {BAND_URL}"
BANDS = [
    {"weightMinKg": None, "weightMaxKg": 55, "doseValue": 260, "doseUnit": "mg"},
    {"weightMinKg": 55, "weightMaxKg": 85, "doseValue": 390, "doseUnit": "mg"},
    {"weightMinKg": 85, "weightMaxKg": None, "doseValue": 520, "doseUnit": "mg"},
]
ADD_PLAN = {
    "action": "draft",
    "targets": [
        {"nodeId": "IBD-N54", "instruction": "add induction", "url": BAND_URL, "mode": "add"},
        {"nodeId": "IBD-N54", "instruction": "reword", "url": BAND_URL, "mode": "update"},
    ],
    "summary": "Add weight-band IV induction beside maintenance.",
}
ADD_DRAFT = {
    "status": "updated",
    "label": "Ustekinumab IV induction, weight-based",
    "content": "One intravenous induction infusion chosen by body weight, before maintenance.",
    "section": "Dosing",
    "fields": {
        "route": "intravenous",
        "doseBands": BANDS,
        "frequency": "once",
        "duration": "single induction dose",
    },
}
ADD = {"match": "Mode: add", "reply": ADD_DRAFT}
UPDATE = {
    "match": "Mode: update",
    "reply": {
        "status": "updated",
        "content": "After the induction infusion, 90 mg is given under the skin every 8 weeks.",
    },
}


@pytest.fixture
def serve_bands(http: respx.MockRouter) -> respx.Route:
    return http.get(BAND_URL).mock(
        return_value=httpx.Response(200, text=BAND_PAGE, headers={"content-type": "text/html"})
    )


def test_the_ustekinumab_request_runs_from_url_to_a_published_cited_node(
    make_service: Callable[..., UpdateService], script: Callable[..., Path], serve_bands: Any
) -> None:
    folder = script([("Synthetic biologic dosing note", ADD_PLAN)], ADD, UPDATE)
    service = make_service(folder)
    thread = UpdateAssistant(service).send(DOCTOR, REQUEST)
    assert thread.status == "proposed" and thread.rounds == 0
    assert len(thread.messages) == 2, "no clarifying question"
    assert "IBD-N104 (new), IBD-N54" in thread.messages[-1].text
    proposal = service.get_proposal(thread.messages[-1].proposal_id or "")

    added, reworded = proposal.changes
    assert added.before is None and added.node_id == "IBD-N104"
    fields = added.after["fields"]
    assert [b["doseValue"] for b in fields["doseBands"]] == [260, 390, 520]
    assert fields["doseBasis"] == "weight_band" and fields["route"] == "intravenous"
    assert fields["drug"] == "ustekinumab", "the rest comes from the neighbour"
    assert added.after["type"] == "drug" and added.after["column"] == "treatment"
    assert added.source_url == BAND_URL and not added.copy_flag
    assert "260 mg" in (added.source_passage or "") and "520 mg" in (added.source_passage or "")

    source = proposal.change_set.add_sources[0]
    assert source.source_id == "IBD-S21" and source.url == BAND_URL
    assert source.title == "Synthetic biologic dosing note" and source.section == "Dosing"
    assert added.after["sourceIds"] == ["IBD-S21"]
    assert reworded.node_id == "IBD-N54" and reworded.before
    assert reworded.after["sourceIds"] == ["IBD-S5", "IBD-S19", "IBD-S21"]
    assert reworded.after["fields"] == reworded.before["fields"], "maintenance dose is untouched"

    service.publish(proposal.proposal_id, REVIEWER, "ok")
    view = browse.node_view(service, "IBD", None, "IBD-N104")
    assert view["packVersion"] == "IBD 1.2"
    assert [s["url"] for s in view["sources"]] == [BAND_URL]
    assert view["updated"]["updatedByName"] == "Dr. Maya (demo)"
    tiers = {n["nodeId"] for n in view["incoming"]}
    assert tiers == {"IBD-N42", "IBD-N45", "IBD-N46"}
    for tier in tiers:
        listed = browse.node_view(service, "IBD", None, tier)["node"]["fields"]["drugNodeIds"]
        assert {"IBD-N54", "IBD-N104"} <= set(listed)


def test_the_api_reports_the_cited_source_with_the_proposal(
    make_service: Callable[..., UpdateService], script: Callable[..., Path], serve_bands: Any
) -> None:
    service = make_service(script([("Synthetic biologic dosing note", ADD_PLAN)], ADD, UPDATE))
    app = FastAPI()
    app.include_router(api.router, prefix="/api/knowledge")
    app.dependency_overrides[api.get_update_service] = lambda: service
    with TestClient(app) as client:
        body = client.post(
            "/api/knowledge/updates", json={"text": REQUEST}, headers={"X-Brahma-Profile": DOCTOR}
        ).json()
    cited = body["proposals"][0]["citedSources"]
    assert [(s["sourceId"], s["url"]) for s in cited] == [("IBD-S21", BAND_URL)]


def test_check_the_website_rereads_the_page_instead_of_asking_again(
    make_service: Callable[..., UpdateService], script: Callable[..., Path], serve_bands: Any
) -> None:
    first = {"action": "ask", "questions": ["Is 390 mg IV?", "Does this replace IBD-N54?"]}
    folder = script([("check the website", ADD_PLAN), ("doctor:", first)], ADD, UPDATE)
    bot = assistant(make_service, folder)
    thread = bot.send(DOCTOR, REQUEST)
    assert thread.status == "open"
    thread = bot.send(DOCTOR, "check the website", thread.thread_id)
    assert thread.status == "proposed" and thread.messages[-1].proposal_id
    assert serve_bands.call_count == 2, "the URL from the first message is read on every turn"


def test_the_page_reaches_the_model_before_it_decides(
    make_service: Callable[..., UpdateService], script: Callable[..., Path], serve_bands: Any
) -> None:
    folder = script([("Above 85 kg: 520 mg IV", ADD_PLAN)], ADD, UPDATE)
    thread = assistant(make_service, folder).send(DOCTOR, REQUEST)
    assert thread.status == "proposed", "the first model call already holds the page text"


def test_the_same_question_is_never_asked_twice(
    make_service: Callable[..., UpdateService], script: Callable[..., Path], serve_bands: Any
) -> None:
    same = {"action": "ask", "questions": ["What is the dose above 85 kg?"]}
    bot = assistant(make_service, script([("doctor:", same)]))
    thread = bot.send(DOCTOR, REQUEST)
    assert thread.messages[-1].text == "What is the dose above 85 kg?"
    thread = bot.send(DOCTOR, "try IBD-N54 and 90 mg", thread.thread_id)
    last = thread.messages[-1].text
    assert thread.status == "stuck" and "instead of asking again" in last
    assert "85 kg" not in last


def test_only_the_new_question_is_asked_on_a_later_round(
    make_service: Callable[..., UpdateService], script: Callable[..., Path], serve_bands: Any
) -> None:
    both = {"action": "ask", "questions": ["What is the dose above 85 kg?", "Which tier applies?"]}
    one = {"action": "ask", "questions": ["What is the dose above 85 kg?"]}
    bot = assistant(make_service, script([("it is IBD-N54", both), ("doctor:", one)]))
    thread = bot.send(DOCTOR, REQUEST)
    thread = bot.send(DOCTOR, "it is IBD-N54", thread.thread_id)
    assert thread.status == "open" and thread.messages[-1].text == "Which tier applies?"


def test_an_unreadable_source_is_reported_without_a_model_call(
    make_service: Callable[..., UpdateService], tmp_path: Path, http: respx.MockRouter
) -> None:
    http.get(BAND_URL).mock(return_value=httpx.Response(403))
    thread = assistant(make_service, tmp_path / "no-replies").send(DOCTOR, REQUEST)
    assert thread.status == "open" and "could not read" in thread.messages[-1].text


def test_bands_that_miss_a_weight_are_not_drafted(
    make_service: Callable[..., UpdateService], script: Callable[..., Path], serve_bands: Any
) -> None:
    partial = {**ADD_DRAFT, "fields": {**ADD_DRAFT["fields"], "doseBands": BANDS[:2]}}
    plan = {**ADD_PLAN, "targets": ADD_PLAN["targets"][:1]}
    folder = script([("Synthetic", plan)], {"match": "Mode: add", "reply": partial})
    thread = assistant(make_service, folder).send(DOCTOR, REQUEST)
    assert thread.status == "open" and "I could not draft" in thread.messages[-1].text


def test_a_band_dose_the_page_does_not_state_is_not_drafted(
    make_service: Callable[..., UpdateService], script: Callable[..., Path], serve_bands: Any
) -> None:
    wrong = [*BANDS[:2], {**BANDS[2], "doseValue": 777}]
    draft = {**ADD_DRAFT, "fields": {**ADD_DRAFT["fields"], "doseBands": wrong}}
    plan = {**ADD_PLAN, "targets": ADD_PLAN["targets"][:1]}
    folder = script([("Synthetic", plan)], {"match": "Mode: add", "reply": draft})
    thread = assistant(make_service, folder).send(DOCTOR, REQUEST)
    assert (
        thread.status == "open" and "does not clearly state doseBands" in thread.messages[-1].text
    )


def test_a_number_in_the_wording_the_page_does_not_state_is_not_drafted(
    make_service: Callable[..., UpdateService], script: Callable[..., Path], serve_bands: Any
) -> None:
    draft = {**ADD_DRAFT, "content": "One infusion of 615 mg by body weight."}
    plan = {**ADD_PLAN, "targets": ADD_PLAN["targets"][:1]}
    folder = script([("Synthetic", plan)], {"match": "Mode: add", "reply": draft})
    thread = assistant(make_service, folder).send(DOCTOR, REQUEST)
    assert thread.status == "open" and "numbers in its wording" in thread.messages[-1].text


def test_keys_the_node_type_does_not_have_are_dropped(
    make_service: Callable[..., UpdateService], script: Callable[..., Path], serve_bands: Any
) -> None:
    fields = {**ADD_DRAFT["fields"], "indications": ["colitis"], "doseBasis": "weight-tiered"}
    plan = {**ADD_PLAN, "targets": ADD_PLAN["targets"][:1]}
    folder = script(
        [("Synthetic", plan)], {"match": "Mode: add", "reply": {**ADD_DRAFT, "fields": fields}}
    )
    bot = assistant(make_service, folder)
    thread = bot.send(DOCTOR, REQUEST)
    assert thread.status == "proposed"
    after = bot._service.get_proposal(thread.messages[-1].proposal_id or "").changes[0].after
    assert "indications" not in after["fields"] and after["fields"]["doseBasis"] == "weight_band"


def test_one_target_per_band_is_merged_into_one_node(
    make_service: Callable[..., UpdateService], script: Callable[..., Path], serve_bands: Any
) -> None:
    split = [
        {"nodeId": "IBD-N54", "instruction": f"band {i}", "url": None, "mode": "add"}
        for i in ("alpha", "bravo", "charlie")
    ]
    folder = script(
        [("Synthetic", {**ADD_PLAN, "targets": split})],
        {"match": "band alpha; band bravo; band charlie", "reply": ADD_DRAFT},
    )
    bot = assistant(make_service, folder)
    thread = bot.send(DOCTOR, REQUEST)
    proposal = bot._service.get_proposal(thread.messages[-1].proposal_id or "")
    assert [c.node_id for c in proposal.changes] == ["IBD-N104"]
    assert len(proposal.changes[0].after["fields"]["doseBands"]) == 3


def test_a_rejected_draft_is_retried_with_the_reason_before_anything_reaches_the_doctor(
    make_service: Callable[..., UpdateService], script: Callable[..., Path], serve_bands: Any
) -> None:
    single = {
        "status": "updated",
        "label": "Ustekinumab 260 mg IV",
        "content": "One infusion of 260 mg.",
        "fields": {"route": "intravenous", "doseValue": 260, "weightMaxKg": 55},
    }
    plan = {**ADD_PLAN, "targets": ADD_PLAN["targets"][:1]}
    folder = script(
        [("Synthetic", plan)],
        {"match": "previous draft was rejected: a dose that depends on weight", "reply": ADD_DRAFT},
        {"match": "Mode: add", "reply": single},
    )
    bot = assistant(make_service, folder)
    thread = bot.send(DOCTOR, REQUEST)
    assert thread.status == "proposed" and len(thread.messages) == 2
    after = bot._service.get_proposal(thread.messages[-1].proposal_id or "").changes[0].after
    assert [b["doseValue"] for b in after["fields"]["doseBands"]] == [260, 390, 520]


def test_a_draft_that_stays_rejected_blames_the_draft_not_the_source(
    make_service: Callable[..., UpdateService], script: Callable[..., Path], serve_bands: Any
) -> None:
    long_label = {**ADD_DRAFT, "label": "x" * 79 + " tail"}
    plan = {**ADD_PLAN, "targets": ADD_PLAN["targets"][:1]}
    folder = script([("Synthetic", plan)], {"match": "Mode: add", "reply": long_label})
    thread = assistant(make_service, folder).send(DOCTOR, REQUEST)
    assert thread.status == "open" and "I could not draft" in thread.messages[-1].text


def test_the_passage_follows_the_model_evidence_and_stays_real_page_text(
    make_service: Callable[..., UpdateService], script: Callable[..., Path], serve_bands: Any
) -> None:
    plan = {**ADD_PLAN, "targets": ADD_PLAN["targets"][1:]}
    reply = {**UPDATE["reply"], "evidence": "Unrelated text about storage, invented claim"}
    folder = script([("Synthetic", plan)], {"match": "Mode: update", "reply": reply})
    bot = assistant(make_service, folder)
    thread = bot.send(DOCTOR, REQUEST)
    passage = bot._service.get_proposal(thread.messages[-1].proposal_id or "").changes[0]
    assert "storage of the invented product" in (passage.source_passage or "")
    assert "invented claim" not in (passage.source_passage or "")


def test_a_new_node_needs_a_label_and_content(
    make_service: Callable[..., UpdateService], script: Callable[..., Path], serve_bands: Any
) -> None:
    plan = {**ADD_PLAN, "targets": ADD_PLAN["targets"][:1]}
    draft = {**ADD_DRAFT, "label": None}
    folder = script([("Synthetic", plan)], {"match": "Mode: add", "reply": draft})
    thread = assistant(make_service, folder).send(DOCTOR, REQUEST)
    assert thread.status == "open" and "both a label and content" in thread.messages[-1].text


def test_a_dose_the_doctor_wrote_that_the_page_lacks_is_called_out(
    make_service: Callable[..., UpdateService], script: Callable[..., Path], serve_bands: Any
) -> None:
    folder = script([("Synthetic", ADD_PLAN)], ADD, UPDATE)
    thread = assistant(make_service, folder).send(DOCTOR, f"set 300 mg IV from {BAND_URL}")
    assert thread.status == "proposed"
    assert "You mentioned 300 mg" in thread.messages[-1].text


def test_open_proposals_share_a_source_and_never_share_new_ids(
    make_service: Callable[..., UpdateService], script: Callable[..., Path], serve_bands: Any
) -> None:
    plan = {**ADD_PLAN, "targets": ADD_PLAN["targets"][:1]}
    service = make_service(script([("Synthetic", plan)], ADD))
    bot = UpdateAssistant(service)
    first = service.get_proposal(bot.send(DOCTOR, REQUEST).messages[-1].proposal_id or "")
    second = service.get_proposal(bot.send(DOCTOR, REQUEST).messages[-1].proposal_id or "")
    assert first.changes[0].node_id == "IBD-N104" and second.changes[0].node_id == "IBD-N105"
    assert first.change_set.add_sources == second.change_set.add_sources
    assert not {e.edge_id for e in first.change_set.add_edges} & {
        e.edge_id for e in second.change_set.add_edges
    }
    service.publish(first.proposal_id, REVIEWER, "ok")
    published = service.publish(second.proposal_id, REVIEWER, "ok")
    assert published.published_version == "1.3"
    third = service.get_proposal(bot.send(DOCTOR, REQUEST).messages[-1].proposal_id or "")
    assert third.change_set.add_sources == [], "the source is already in the pack"
    assert third.changes[0].after["sourceIds"] == ["IBD-S21"]


def test_the_offline_demo_fixture_runs_the_ustekinumab_example(
    make_service: Callable[..., UpdateService], http: respx.MockRouter
) -> None:
    url = "https://reference.medscape.com/drug/stelara-wezlana-ustekinumab-345050"
    http.get(url).mock(
        return_value=httpx.Response(200, text=BAND_PAGE, headers={"content-type": "text/html"})
    )
    demo = Path(__file__).parents[1] / "agent" / "fixtures" / "recorded" / "demo"
    bot = assistant(make_service, demo)
    thread = bot.send(DOCTOR, f"update ustekinumab dose from {url}")
    assert thread.status == "proposed"
    change = bot._service.get_proposal(thread.messages[-1].proposal_id or "").changes[0]
    assert change.before is None
    assert [b["doseValue"] for b in change.after["fields"]["doseBands"]] == [260, 390, 520]
    plain = bot.send(DOCTOR, "Update ustekinumab maintenance dose")
    assert plain.status == "open" and "source URL" in plain.messages[-1].text


def test_threads_are_private_to_their_doctor(
    make_service: Callable[..., UpdateService], script: Callable[..., Path]
) -> None:
    bot = assistant(make_service, script([("doctor:", ASK)]))
    thread = bot.send(DOCTOR, "update something")
    with pytest.raises(ThreadNotFound):
        bot.get_thread(thread.thread_id, REVIEWER)
    assert ModelUnavailable  # imported for the failure test above


def test_attribution_is_recorded_when_a_proposal_is_published(
    make_service: Callable[..., UpdateService], script: Callable[..., Path], serve: None
) -> None:
    folder = script([("https://", interpret("IBD-N54"))], updated("IBD-N54"))
    service = make_service(folder)
    thread = UpdateAssistant(service).send(DOCTOR, f"update from {URL}")
    pid = thread.messages[-1].proposal_id or ""
    before = browse.node_view(service, "IBD", None, "IBD-N54")
    assert before["updated"] is None and before["initialVersion"] == "1.1"
    service.publish(pid, REVIEWER, "ok")
    after = browse.node_view(service, "IBD", None, "IBD-N54")
    assert after["updated"]["updatedByName"] == "Dr. Maya (demo)"
    assert after["updated"]["approvedByName"] == "Demo clinical reviewer"
    assert after["updated"]["version"] == "1.2" and after["updated"]["proposalId"] == pid
    old = browse.node_view(service, "IBD", "1.1", "IBD-N54")
    assert old["updated"] is None
    graph = browse.pack_graph(service, "IBD", None)
    stamps = {n["nodeId"]: n["updatedAt"] for n in graph["nodes"]}
    assert stamps["IBD-N54"] and stamps["IBD-N57"] is None
    history = service.version_history("IBD")
    assert history[0].author_name == "Demo clinical reviewer"


def test_browse_reads_the_structure(updates: UpdateService) -> None:
    packs = browse.list_packs(updates)
    assert packs[0]["pack"] == "IBD" and packs[0]["liveVersion"] == "1.1"
    graph = browse.pack_graph(updates, "IBD", None)
    assert len(graph["nodes"]) > 50 and graph["edges"][0]["label"]
    node_id = graph["edges"][0]["from"]
    view = browse.node_view(updates, "IBD", None, node_id)
    assert view["outgoing"] and view["sources"] and view["packVersion"] == "IBD 1.1"
    target = view["outgoing"][0]["nodeId"]
    incoming = browse.node_view(updates, "IBD", None, target)["incoming"]
    assert node_id in {n["nodeId"] for n in incoming}
    conditional = [e for e in graph["edges"] if "(" in e["label"]]
    assert conditional
    with pytest.raises(NodeNotFound):
        browse.node_view(updates, "IBD", None, "IBD-N9999")
    with pytest.raises(VersionNotFound):
        browse.pack_graph(updates, "IBD", "9.9")


def test_api_conversation_and_browse(
    make_service: Callable[..., UpdateService], script: Callable[..., Path], serve: None
) -> None:
    folder = script([("https://", interpret("IBD-N54")), ("doctor:", ASK)], updated("IBD-N54"))
    service = make_service(folder)
    app = FastAPI()
    app.include_router(api.router, prefix="/api/knowledge")
    app.dependency_overrides[api.get_update_service] = lambda: service
    headers = {"X-Brahma-Profile": DOCTOR}
    with TestClient(app) as client:
        first = client.post("/api/knowledge/updates", json={"text": "update"}, headers=headers)
        assert first.status_code == 200 and first.json()["rounds"] == 1
        tid = first.json()["threadId"]
        second = client.post(
            "/api/knowledge/updates", json={"text": f"use {URL}", "threadId": tid}, headers=headers
        )
        body = second.json()
        assert body["status"] == "proposed" and body["proposals"][0]["proposerName"]
        assert client.get(f"/api/knowledge/updates/{tid}", headers=headers).json() == body
        assert len(client.get("/api/knowledge/updates", headers=headers).json()["threads"]) == 1
        missing = client.get("/api/knowledge/updates/nope", headers=headers)
        assert missing.status_code == 404
        blank = client.post("/api/knowledge/updates", json={"text": ""}, headers=headers)
        assert blank.status_code == 422
        assert (
            client.get("/api/knowledge/packs", headers=headers).json()["packs"][0]["pack"] == "IBD"
        )
        graph = client.get("/api/knowledge/graph?pack=IBD", headers=headers).json()
        assert graph["version"] == "1.1"
        detail = client.get("/api/knowledge/nodes/IBD-N54?pack=IBD&version=1.1", headers=headers)
        assert detail.json()["node"]["nodeId"] == "IBD-N54"
        assert client.get("/api/knowledge/nodes/IBD-NX", headers=headers).status_code == 404
        assert client.get("/api/knowledge/graph?version=9.9", headers=headers).status_code == 404
        assert client.get("/api/knowledge/packs").status_code == 401
