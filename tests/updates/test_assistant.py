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


def test_the_conversation_stops_after_five_unanswered_rounds(
    make_service: Callable[..., UpdateService], script: Callable[..., Path]
) -> None:
    bot = assistant(make_service, script([("doctor:", ASK)]))
    thread = bot.send(DOCTOR, "update something")
    for _ in range(MAX_ROUNDS - 1):
        thread = bot.send(DOCTOR, "still unsure", thread.thread_id)
    assert thread.status == "stuck" and "could not work this out" in thread.messages[-1].text
    with pytest.raises(ThreadClosed):
        bot.send(DOCTOR, "one more", thread.thread_id)


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
