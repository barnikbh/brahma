"""The C8 core API through FastAPI's TestClient (plan Step 13; C7, C8, BR4)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from brahma.agent.models import DISCLAIMER
from brahma.knowledge import ChangeSet, KnowledgeService, PackVersionRef
from brahma.knowledge.db import kg_connect
from brahma.server.services import Services, load_initial_packs
from tests.agent.conftest import DEMO_RESULTS, DEMO_TEXT, DOCTOR, PROJECT_ROOT
from tests.server.conftest import TAB, new_case, sse

TAB_HEADERS = {"X-Brahma-Tab": TAB}
PROTECTED = [
    ("GET", "/api/features"),
    ("GET", "/api/session"),
    ("POST", "/api/disclaimer"),
    ("GET", "/api/patients?q=BR"),
    ("POST", "/api/patients"),
    ("GET", "/api/cases/BR-000000"),
    ("POST", "/api/cases/BR-000000/lock"),
    ("POST", "/api/cases/BR-000000/messages"),
    ("PATCH", "/api/cases/BR-000000/patient"),
    ("PUT", "/api/cases/BR-000000/forms/msg-1/draft"),
    ("POST", "/api/cases/BR-000000/walk"),
    ("GET", "/api/cases/BR-000000/map"),
    ("POST", "/api/cases/BR-000000/treatment-edits"),
    ("POST", "/api/cases/BR-000000/traverse"),
    ("GET", "/api/nodes/IBD@1.1/IBD-N1"),
    ("GET", "/api/nodes/IBD@1.1/IBD-N1/comments"),
    ("POST", "/api/nodes/IBD@1.1/IBD-N1/comments"),
    ("GET", "/api/sessions"),
    ("GET", "/api/sessions/s-1"),
    ("GET", "/api/sessions/s-1/export"),
    ("GET", "/api/knowledge/proposals"),
]


def _walk(client: TestClient, case_id: str, **body: Any) -> list[tuple[str, dict[str, Any]]]:
    response = client.post(f"/api/cases/{case_id}/walk", json=body, headers=TAB_HEADERS)
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/event-stream")
    return sse(response.text)


def _payloads(events: list[tuple[str, dict[str, Any]]], kind: str) -> list[dict[str, Any]]:
    return [data for name, data in events if name == kind]


def _demo_walk(client: TestClient, case_id: str) -> list[tuple[str, dict[str, Any]]]:
    events = _walk(client, case_id, mode="start", text=DEMO_TEXT)
    form = _payloads(events, "form")[0]
    findings = [
        {
            "kind": f["findingKind"],
            "name": f["name"],
            "value": f["value"],
            "unit": f["unit"],
            "duration": f["duration"],
        }
        for f in form["fields"]
    ]
    step = _walk(
        client,
        case_id,
        mode="continue",
        walkId=form["walkId"],
        formMessageId=form["messageId"],
        formValues={"findings": findings},
    )
    events += step
    for answers in DEMO_RESULTS:
        needs = _payloads(step, "form")[0]
        step = _walk(
            client,
            case_id,
            mode="continue",
            walkId=form["walkId"],
            formMessageId=needs["messageId"],
            formValues=answers,
        )
        events += step
    return events


@pytest.mark.parametrize(("method", "path"), PROTECTED)
def test_every_route_needs_a_session(anon: TestClient, method: str, path: str) -> None:
    response = anon.request(method, path, json={}, headers={"X-Brahma-Profile": DOCTOR})
    assert response.status_code == 401, (method, path, response.text)
    assert response.json()["error"]["code"] in ("not_signed_in", "NotSignedIn")


def test_sign_in_and_the_disclaimer(anon: TestClient) -> None:
    profiles = anon.get("/api/profiles").json()["profiles"]
    assert {p["profileId"] for p in profiles} == {"p-maya", "p-urologist", "p-reviewer"}
    assert anon.post("/api/session", json={"profileId": "p-benchmark"}).status_code == 404
    signed = anon.post("/api/session", json={"profileId": DOCTOR})
    assert signed.status_code == 200
    cookie = signed.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=Lax" in cookie
    view = signed.json()
    assert view["needsDisclaimer"] is True
    assert view["packVersions"] == "IBD 1.1; URO 0.1"
    assert view["disclaimer"]["text"].startswith(DISCLAIMER)
    accepted = anon.post("/api/disclaimer").json()
    assert accepted["disclaimer"] == DISCLAIMER
    assert anon.get("/api/session").json()["needsDisclaimer"] is False
    tampered = cookie.split(";")[0].split("=", 1)[1] + "0"
    anon.cookies.clear()
    anon.cookies.set("brahma_session", tampered)
    assert anon.get("/api/session").status_code == 401  # a tampered cookie is ignored
    assert anon.delete("/api/session").status_code == 204


def test_create_and_search_patients(client: TestClient) -> None:
    case_id = new_case(client)
    found = client.get("/api/patients", params={"q": case_id}).json()["results"]
    assert [r["caseId"] for r in found] == [case_id]
    assert client.get("/api/patients", params={"q": "  "}).json()["results"] == found
    view = client.get(f"/api/cases/{case_id}").json()
    assert view["case"]["synthetic"] is True and view["disclaimer"] == DISCLAIMER
    bad = client.post(
        "/api/patients", json={"syntheticName": "X", "age": 30, "sex": "female", "mrn": "12345"}
    )
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "invalid_request"


def test_lock_held_and_read_only_tabs_get_409(client: TestClient) -> None:
    case_id = new_case(client)
    other = client.post(f"/api/cases/{case_id}/lock", json={"tabId": "tab-2"}).json()
    assert other == {"state": "read_only"}
    blocked = client.post(
        f"/api/cases/{case_id}/walk",
        json={"mode": "start", "text": DEMO_TEXT},
        headers={"X-Brahma-Tab": "tab-2"},
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "case_read_only"
    no_tab = client.post(f"/api/cases/{case_id}/messages", json={"text": "hello"})
    assert no_tab.status_code == 409
    assert (
        client.request("DELETE", f"/api/cases/{case_id}/lock", json={"tabId": TAB}).status_code
        == 204
    )
    assert client.post(f"/api/cases/{case_id}/lock", json={"tabId": "tab-2"}).json() == {
        "state": "held"
    }


def test_sse_demo_walk_streams_progress_lines_and_done(client: TestClient) -> None:
    case_id = new_case(client)
    first = _walk(client, case_id, mode="start", text=DEMO_TEXT)
    assert first[0] == ("progress", {"step": "reading_findings"})
    events = _demo_walk(client, case_id)
    assert _payloads(events, "line")
    done = _payloads(events, "done")[0]
    assert done["outcome"] == "answered" and done["counts"]["ungrounded"] == 0
    assert (done["packVersion"], done["provider"], done["model"], done["disclaimer"]) == (
        "IBD 1.1",
        "recorded",
        "recorded",
        DISCLAIMER,
    )
    view = client.get(f"/api/cases/{case_id}", headers=TAB_HEADERS).json()
    assert view["walk"]["status"] == "answered" and view["lock"] == "held"
    assert view["pinnedVersion"] == "IBD 1.1" and view["newerVersion"] is None
    assert any(m["kind"] == "pathway" for m in view["messages"])
    mapped = client.get(f"/api/cases/{case_id}/map").json()
    assert {"IBD-N34", "IBD-N41"} <= {n["nodeId"] for n in mapped["nodes"]}
    replay = client.get(f"/api/cases/{case_id}/map", params={"sessionId": done["sessionId"]})
    assert replay.json()["selectedPath"][0] == "IBD-N1"
    retry = _walk(client, case_id, mode="continue", walkId=done["walkId"])
    assert _payloads(retry, "error")[0]["code"] == "walk_not_resumable"


def test_case_view_shows_the_newer_version_banner(client: TestClient, services: Services) -> None:
    case_id = new_case(client)
    _demo_walk(client, case_id)
    base = PackVersionRef(pack="IBD", number="1.1")
    node = services.knowledge.get_node(base, "IBD-N60").model_copy(update={"pack_version": None})
    changes = ChangeSet(
        update_nodes=[node.model_copy(update={"label": "Diet (reviewed)"})],
        change_summary="Label review",
    )
    services.knowledge.create_version("IBD", base, changes, DOCTOR)
    assert client.get(f"/api/cases/{case_id}").json()["newerVersion"] == "IBD 1.2"


def test_node_detail_with_dose_safety_and_comments(client: TestClient) -> None:
    case_id = new_case(client)
    detail = client.get("/api/nodes/IBD@1.1/IBD-N53", params={"caseId": case_id}).json()
    assert detail["node"]["nodeId"] == "IBD-N53"
    assert detail["dose"]["value"] == 290.0 and detail["dose"]["unit"] == "mg"
    assert {s["check"] for s in detail["safety"]} >= {"allergy", "pregnancy"}
    assert (detail["packVersion"], detail["disclaimer"]) == ("IBD 1.1", DISCLAIMER)
    assert [s["sourceId"] for s in detail["sources"]] == ["IBD-S1", "IBD-S5", "IBD-S6"]
    assert client.get("/api/nodes/IBD@9.9/IBD-N53").status_code == 404
    assert client.get("/api/nodes/IBD@1.1/IBD-N999").status_code == 404


def test_node_detail_carries_criterion_targets(client: TestClient) -> None:
    day3 = client.get("/api/nodes/IBD@1.1/IBD-N80").json()
    assert day3["leadsTo"] == [
        {"nodeId": "IBD-N42", "label": "UC Tier 3: rescue or advanced therapy"}
    ]
    watch = client.get("/api/nodes/IBD@1.1/IBD-N90").json()
    assert watch["leadsTo"] == []
    assert client.get("/api/nodes/nonsense/IBD-N1").status_code == 422
    added = client.post("/api/nodes/IBD-1.1/IBD-N53/comments", json={"text": "Check TB first"})
    assert added.status_code == 201 and added.json()["authorProfileId"] == DOCTOR
    listed = client.get("/api/nodes/IBD@1.1/IBD-N53/comments").json()["comments"]
    assert [c["text"] for c in listed] == ["Check TB first"]


def test_chat_after_an_answered_walk_runs_the_follow_up_turn(client: TestClient) -> None:
    case_id = new_case(client)
    _demo_walk(client, case_id)
    assert client.get(f"/api/cases/{case_id}").json()["walk"]["canFollowUp"] is True
    text = "Remicade failed. steroids work. Suggest alternate treatment plan"
    events = _walk(client, case_id, mode="follow_up", text=text)
    assert [name for name, _ in events][:2] == ["progress", "history"]
    assert _payloads(events, "history")[0]["text"].startswith("Noted treatment history:")
    done = _payloads(events, "done")[0]
    assert done["outcome"] == "answered" and done["counts"]["ungrounded"] == 0
    cited = {n for line in _payloads(events, "line") for n in line["nodeIds"]}
    assert "IBD-N54" in cited  # ustekinumab
    view = client.get(f"/api/cases/{case_id}").json()
    assert view["messages"][-1]["body"]["history"][0]["drug"] == "infliximab"
    blank = _walk(client, case_id, mode="follow_up")
    assert _payloads(blank, "error")[0]["code"] == "invalid_request"
    too_long = client.post(
        f"/api/cases/{case_id}/walk",
        json={"mode": "follow_up", "text": "x" * 4001},
        headers=TAB_HEADERS,
    )
    assert too_long.status_code == 422


def test_start_up_loads_a_newer_pack_file_as_a_new_version(tmp_path: Path) -> None:
    content = tmp_path / "content"
    content.mkdir()
    source = (PROJECT_ROOT / "content" / "ibd.yaml").read_text(encoding="utf-8")
    older = source.replace('version: "1.1"', 'version: "1.0"', 1)
    (content / "ibd.yaml").write_text(older, encoding="utf-8")
    knowledge = KnowledgeService(kg_connect(tmp_path / "k.db"))
    try:
        assert load_initial_packs(knowledge, content) == ["IBD 1.0"]
        assert load_initial_packs(knowledge, content) == []  # not newer: skipped
        (content / "ibd.yaml").write_text(source, encoding="utf-8")
        assert load_initial_packs(knowledge, content) == ["IBD 1.1"]
        versions = {v.number: v.status for v in knowledge.list_versions("IBD")}
        assert versions == {"1.1": "live", "1.0": "superseded"}
        (content / "broken.yaml").write_text("pack: [", encoding="utf-8")
        assert load_initial_packs(knowledge, content) == []  # unreadable: kept running
    finally:
        knowledge.close()


def test_treatment_edit_patient_change_message_and_draft(client: TestClient) -> None:
    case_id = new_case(client)
    edit = client.post(
        f"/api/cases/{case_id}/treatment-edits",
        json={"nodeId": "IBD-N52", "newValues": {"doseValue": 40}},
        headers=TAB_HEADERS,
    )
    assert edit.status_code == 201, edit.text
    assert edit.json()["dose"]["value"] == 40.0
    bad = client.post(
        f"/api/cases/{case_id}/treatment-edits",
        json={"nodeId": "IBD-N52", "newValues": {"label": "x"}},
        headers=TAB_HEADERS,
    )
    assert bad.status_code == 422
    patched = client.patch(
        f"/api/cases/{case_id}/patient", json={"weightKg": 62}, headers=TAB_HEADERS
    )
    assert patched.status_code == 200 and patched.json()["patient"]["weightKg"] == 62
    sent = client.post(
        f"/api/cases/{case_id}/messages", json={"text": "she's 62 kg"}, headers=TAB_HEADERS
    )
    assert sent.status_code == 201 and sent.json()["offers"] == []
    empty = client.post(f"/api/cases/{case_id}/messages", json={"text": " "}, headers=TAB_HEADERS)
    assert empty.status_code == 422
    start = _walk(client, case_id, mode="start", text=DEMO_TEXT)
    form_id = _payloads(start, "form")[0]["messageId"]
    saved = client.put(
        f"/api/cases/{case_id}/forms/{form_id}/draft", json={"Hb": "10.2"}, headers=TAB_HEADERS
    )
    assert saved.status_code == 204
    assert client.get(f"/api/cases/{case_id}").json()["formDrafts"] == {form_id: {"Hb": "10.2"}}


def test_node_detail_returns_the_latest_edit_for_its_case(client: TestClient) -> None:
    case_id = new_case(client)
    edit = client.post(
        f"/api/cases/{case_id}/treatment-edits",
        json={"nodeId": "IBD-N52", "newValues": {"doseValue": 40}},
        headers=TAB_HEADERS,
    )
    assert edit.status_code == 201, edit.text
    edited = client.get("/api/nodes/IBD@1.1/IBD-N52", params={"caseId": case_id}).json()["edited"]
    assert edited["editId"] == edit.json()["edit"]["editId"]
    assert edited["newValues"]["doseValue"] == 40
    assert edited["editorProfileId"] == DOCTOR
    other = client.get("/api/nodes/IBD@1.1/IBD-N51", params={"caseId": case_id}).json()
    assert other["edited"] is None
    assert client.get("/api/nodes/IBD@1.1/IBD-N52").json()["edited"] is None


def test_session_history_detail_and_export(client: TestClient) -> None:
    case_id = new_case(client)
    done = _payloads(_demo_walk(client, case_id), "done")[0]
    sessions = client.get("/api/sessions", params={"outcome": "answered"}).json()["sessions"]
    assert [s["sessionId"] for s in sessions] == [done["sessionId"]]
    detail = client.get(f"/api/sessions/{done['sessionId']}").json()
    assert detail["record"]["walkId"] == done["walkId"]
    assert detail["map"]["nodes"] and detail["disclaimer"] == DISCLAIMER
    exported = client.get(f"/api/sessions/{done['sessionId']}/export")
    assert exported.headers["content-type"].startswith("application/json")
    assert exported.json()["record"]["packVersion"] == "IBD 1.1"
    pdf = client.get(f"/api/sessions/{done['sessionId']}/export", params={"format": "pdf"})
    assert pdf.headers["content-type"] == "application/pdf" and pdf.content.startswith(b"%PDF")
    assert client.get("/api/sessions/s-unknown").status_code == 404


def test_knowledge_feature_is_mounted_and_ignores_a_client_profile_header(
    client: TestClient,
) -> None:
    features = client.get("/api/features").json()["features"]
    assert [f["name"] for f in features] == ["knowledge"]
    body = {
        "nodeId": "IBD-N36",
        "change": {"content": "Colonic Crohn's disease, small bowel spared."},
        "comment": "Clearer",
    }
    created = client.post(
        "/api/knowledge/proposals", json=body, headers={"X-Brahma-Profile": "p-reviewer"}
    )
    assert created.status_code == 201, created.text
    assert created.json()["proposerProfileId"] == DOCTOR
    publish = client.post(
        f"/api/knowledge/proposals/{created.json()['proposalId']}/publish",
        json={},
        headers={"X-Brahma-Profile": "p-reviewer"},
    )
    assert publish.status_code == 403  # the session is the doctor, not the reviewer


def test_health_reports_packs_provider_and_database(anon: TestClient) -> None:
    health = anon.get("/api/health").json()
    assert health["status"] == "ok" and health["database"] == "ok"
    assert health["packs"] == [{"pack": "IBD", "number": "1.1"}, {"pack": "URO", "number": "0.1"}]
    assert health["provider"] == {"provider": "recorded", "model": "recorded"}


def test_traverse_route_records_a_choice_and_replays_it(client: TestClient) -> None:
    case_id = new_case(client)
    events = _demo_walk(client, case_id)
    done = _payloads(events, "done")[0]
    response = client.post(
        f"/api/cases/{case_id}/traverse", json={"nodeId": "IBD-N51"}, headers=TAB_HEADERS
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert "Hydrocortisone" in body["notice"]
    statuses = {n["nodeId"]: n["status"] for n in body["map"]["nodes"]}
    assert statuses["IBD-N51"] == "chosen"
    assert statuses["IBD-N52"] == "option"
    assert statuses["IBD-N70"] == "used"
    assert statuses["IBD-N42"] == "planned"
    assert body["path"]["drug"]["nodeId"] == "IBD-N51"
    assert body["path"]["tier"]["nodeId"] == "IBD-N41"
    assert [n["nodeId"] for n in body["path"]["review"]] == ["IBD-N80", "IBD-N81"]
    assert [n["nodeId"] for n in body["path"]["nextTiers"]] == ["IBD-N42"]
    replay = client.get(f"/api/cases/{case_id}/map", params={"sessionId": done["sessionId"]}).json()
    assert replay["selectedPath"][0] == "IBD-N1"
    assert {n["nodeId"]: n["status"] for n in replay["nodes"]}["IBD-N51"] == "chosen"
    bad = client.post(
        f"/api/cases/{case_id}/traverse", json={"nodeId": "IBD-N41"}, headers=TAB_HEADERS
    )
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "traverse_invalid"
    no_tab = client.post(f"/api/cases/{case_id}/traverse", json={"nodeId": "IBD-N52"})
    assert no_tab.status_code == 409
