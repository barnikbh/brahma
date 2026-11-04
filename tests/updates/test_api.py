"""The C9 router through FastAPI's TestClient (plan Step 13; C7, C9, FR10.4, FR10.8, FR10.9)."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

import httpx
import pytest
import respx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from brahma.updates import api
from brahma.updates.service import UpdateService
from tests.updates.conftest import DOCTOR, REVIEWER, SOURCE_URL

COPIED = (
    "This made up page exists only for automated tests of the Brahma update flow and it "
    "describes no real clinical guidance of any kind whatsoever for any patient at all"
)


@pytest.fixture
def client(updates: UpdateService) -> Iterator[TestClient]:
    """The router mounted as U4's server mounts it (C7), with the test service injected."""
    app = FastAPI()
    app.include_router(api.router, prefix=f"/api/{api.feature['name']}")
    app.dependency_overrides[api.get_update_service] = lambda: updates
    with TestClient(app) as test_client:
        yield test_client


def _as(profile: str) -> dict[str, str]:
    return {"X-Brahma-Profile": profile}


DEFAULT_CONTENT = "Colonic Crohn's disease, small bowel spared."


def _create(client: TestClient, content: str = DEFAULT_CONTENT, **extra: Any) -> dict[str, Any]:
    body = {"nodeId": "IBD-N36", "change": {"content": content}, "comment": "Clearer", **extra}
    response = client.post("/api/knowledge/proposals", json=body, headers=_as(DOCTOR))
    assert response.status_code == 201, response.text
    created: dict[str, Any] = response.json()
    return created


def test_feature_entry_follows_the_c7_convention() -> None:
    assert api.feature == {"name": "knowledge", "version": "1.0", "screens": ["knowledge"]}


def test_creating_and_getting_a_proposal_round_trips(client: TestClient) -> None:
    created = _create(client)
    assert created["status"] == "proposed"
    assert created["changes"][0]["after"]["content"].startswith("Colonic Crohn's")
    assert created["copyFlaggedNodeIds"] == []
    fetched = client.get(f"/api/knowledge/proposals/{created['proposalId']}", headers=_as(DOCTOR))
    assert fetched.status_code == 200
    assert fetched.json() == created
    listed = client.get("/api/knowledge/proposals?pack=IBD&status=proposed", headers=_as(DOCTOR))
    assert [p["proposalId"] for p in listed.json()["proposals"]] == [created["proposalId"]]


def test_publishing_as_a_doctor_returns_403_with_a_plain_message(client: TestClient) -> None:
    created = _create(client)
    response = client.post(
        f"/api/knowledge/proposals/{created['proposalId']}/publish", json={}, headers=_as(DOCTOR)
    )
    assert response.status_code == 403
    assert response.json()["error"] == {"code": "Forbidden", "message": api.FORBIDDEN_MESSAGE}
    reject = client.post(
        f"/api/knowledge/proposals/{created['proposalId']}/reject",
        json={"comment": "no"},
        headers=_as(DOCTOR),
    )
    assert reject.status_code == 403


def test_publishing_a_flagged_proposal_returns_409(
    client: TestClient, page: Callable[..., respx.Route]
) -> None:
    page()
    created = _create(client, COPIED, sourceUrl=SOURCE_URL)
    assert created["copyFlaggedNodeIds"] == ["IBD-N36"]
    response = client.post(
        f"/api/knowledge/proposals/{created['proposalId']}/publish", json={}, headers=_as(REVIEWER)
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CopyFlagged"
    assert "paraphrase" in response.json()["error"]["message"]


def test_publishing_as_the_reviewer_returns_200_and_the_versions_list_shows_it(
    client: TestClient,
) -> None:
    created = _create(client)
    response = client.post(
        f"/api/knowledge/proposals/{created['proposalId']}/publish",
        json={"comment": "Matches the source"},
        headers=_as(REVIEWER),
    )
    assert response.status_code == 200
    assert response.json()["publishedVersion"] == "1.3"
    again = client.post(
        f"/api/knowledge/proposals/{created['proposalId']}/reject",
        json={"comment": "late"},
        headers=_as(REVIEWER),
    )
    assert again.status_code == 409
    versions = client.get("/api/knowledge/versions?pack=IBD", headers=_as(DOCTOR)).json()
    assert [(v["version"], v["status"]) for v in versions["versions"]] == [
        ("1.3", "live"),
        ("1.2", "superseded"),
    ]
    assert versions["versions"][0]["comment"] == "Matches the source"


def test_refused_urls_and_invalid_changes_return_422(client: TestClient) -> None:
    refused = client.post(
        "/api/knowledge/proposals",
        json={
            "nodeId": "IBD-N36",
            "change": {"content": "x"},
            "comment": "c",
            "sourceUrl": "http://127.0.0.1/",
        },
        headers=_as(DOCTOR),
    )
    assert refused.status_code == 422
    assert refused.json()["error"]["code"] == "SourceFetchError"
    invalid = client.post(
        "/api/knowledge/proposals",
        json={"nodeId": "IBD-N36", "change": {"type": "drug"}, "comment": "c"},
        headers=_as(DOCTOR),
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "ProposalInvalid"
    draft = client.post(
        "/api/knowledge/proposals/draft", json={"url": "ftp://x.example.org/"}, headers=_as(DOCTOR)
    )
    assert draft.status_code == 422


def test_fetch_failures_return_502_and_drafting_works(
    client: TestClient, http: respx.MockRouter, page: Callable[..., respx.Route]
) -> None:
    down = "https://down.example.org/page"
    http.get(down).mock(return_value=httpx.Response(500))
    failed = client.post("/api/knowledge/proposals/draft", json={"url": down}, headers=_as(DOCTOR))
    assert failed.status_code == 502
    assert "HTTP 500" in failed.json()["error"]["message"]
    page()
    drafted = client.post(
        "/api/knowledge/proposals/draft", json={"url": SOURCE_URL}, headers=_as(DOCTOR)
    )
    assert drafted.status_code == 201
    assert drafted.json()["origin"] == "drafted"


def test_unknown_proposals_and_missing_sign_in(client: TestClient) -> None:
    missing = client.get("/api/knowledge/proposals/pr-missing", headers=_as(DOCTOR))
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "ProposalNotFound"
    unsigned = client.get("/api/knowledge/proposals")
    assert unsigned.status_code == 401
    unknown_profile = _create_raw(client, "p-nobody")
    assert unknown_profile.status_code == 404


def _create_raw(client: TestClient, profile: str) -> Any:
    body = {"nodeId": "IBD-N36", "change": {"content": "x y z"}, "comment": "c"}
    return client.post("/api/knowledge/proposals", json=body, headers=_as(profile))


def test_unmapped_errors_are_left_to_the_server_and_the_default_service_opens(
    updates: UpdateService, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert api.error_response(RuntimeError("boom")) is None
    monkeypatch.setattr(api, "_service", None)
    service = api.get_update_service()
    try:
        assert api.get_update_service() is service
    finally:
        service.close()
        monkeypatch.setattr(api, "_service", None)
