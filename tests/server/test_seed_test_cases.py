"""``scripts/seed_test_cases.py``: a fresh database with one synthetic patient per test.

The seed runs against a temporary file, then the real app is started on it with the
recorded demo replies, so the seeded patients are walked exactly as a doctor would.
"""

from __future__ import annotations

import importlib.util
import secrets
import sqlite3
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from fastapi.testclient import TestClient

from brahma.server.app import create_app
from brahma.server.config import ServerConfig
from tests.agent.conftest import DOCTOR, PROJECT_ROOT, make_gateway_for, recorded
from tests.server.conftest import TAB
from tests.server.test_api import _demo_walk, _payloads, _walk

TAB_HEADERS = {"X-Brahma-Tab": TAB}


def _load_seed() -> ModuleType:
    path = PROJECT_ROOT / "scripts" / "seed_test_cases.py"
    spec = importlib.util.spec_from_file_location("seed_test_cases", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


seed_module = _load_seed()


@pytest.fixture
def seeded(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    db = tmp_path / "brahma.db"
    made = seed_module.seed(db)
    return db, {case.tid: case_id for case, case_id in made}


def _client(db: Path, tmp_path: Path) -> TestClient:
    """The real app on the seeded database; use it in a ``with`` block."""
    config = ServerConfig(
        session_secret=secrets.token_urlsafe(32),
        log_path=tmp_path / "brahma.log",
        db_path=db,
        content_dir=PROJECT_ROOT / "content",
    )
    app = create_app(config, gateway_factory=lambda conn: make_gateway_for(conn, recorded("demo")))
    return TestClient(app)


def _sign_in(client: TestClient, profile: str = DOCTOR) -> None:
    assert client.post("/api/session", json={"profileId": profile}).status_code == 200
    assert client.post("/api/disclaimer").status_code == 200


def test_seed_creates_every_case_with_its_note_and_both_pack_versions(
    seeded: tuple[Path, dict[str, str]],
) -> None:
    db, ids = seeded
    assert list(ids) == [case.tid for case in seed_module.CASES]
    conn = sqlite3.connect(db)
    versions = dict(conn.execute("SELECT pack_version_id, status FROM kg_pack_version"))
    assert versions == {"IBD@1.0": "superseded", "IBD@1.2": "live", "URO@0.1": "live"}
    rows = conn.execute(
        "SELECT c.case_id, c.owner_profile_id, c.status, json_extract(p.body_json, "
        "'$.syntheticName') FROM cs_case c JOIN cs_patient p USING (patient_id)"
    ).fetchall()
    assert len(rows) == len(seed_module.CASES)
    assert all(name.endswith("(synthetic)") and status == "new" for _, _, status, name in rows)
    owners = {case_id: owner for case_id, owner, _, _ in rows}
    assert owners[ids["U01"]] == owners[ids["U02"]] == "p-urologist"
    assert owners[ids["T01"]] == "p-maya"
    notes = conn.execute("SELECT body_json FROM cs_message WHERE author = 'brahma'").fetchall()
    assert len(notes) == len(seed_module.CASES)
    assert all("docs/test-cases.md" in body for (body,) in notes)


def test_seeded_patients_list_newest_first_with_t01_on_top(
    seeded: tuple[Path, dict[str, str]], tmp_path: Path
) -> None:
    db, ids = seeded
    with _client(db, tmp_path) as client:
        _sign_in(client)
        results = client.get("/api/patients", params={"q": ""}).json()["results"]
    listed = [p["caseId"] for p in results]
    assert listed[0] == ids["T01"]
    assert ids["U01"] not in listed  # the urologist's patients are theirs


def test_the_seeded_demo_case_walks_offline_to_an_answer(
    seeded: tuple[Path, dict[str, str]], tmp_path: Path
) -> None:
    db, ids = seeded
    with _client(db, tmp_path) as client:
        _sign_in(client)
        view = client.get(f"/api/cases/{ids['T01']}", headers=TAB_HEADERS).json()
        assert view["walk"] is None  # the note does not count as a walk
        done = _payloads(_demo_walk(client, ids["T01"]), "done")[0]
    assert done["outcome"] == "answered" and done["counts"]["ungrounded"] == 0
    assert done["packVersion"].endswith("1.2")


def test_the_case_pinned_to_ibd_1_0_walks_on_1_0_and_offers_the_newer_version(
    seeded: tuple[Path, dict[str, str]], tmp_path: Path
) -> None:
    db, ids = seeded
    case_id = ids["T16"]
    with _client(db, tmp_path) as client:
        _sign_in(client)
        done = _payloads(_demo_walk(client, case_id), "done")[0]
        view: dict[str, Any] = client.get(f"/api/cases/{case_id}", headers=TAB_HEADERS).json()
        follow = _walk(client, case_id, mode="follow_up", text="Remicade failed. steroids work.")
    assert done["outcome"] == "answered" and done["packVersion"].endswith("1.0")
    assert "1.2" in str(view.get("newerVersion"))
    assert _payloads(follow, "done")[0]["outcome"] == "out_of_knowledge"


def test_the_guide_is_in_step_with_the_cases() -> None:
    guide = (PROJECT_ROOT / "docs" / "test-cases.md").read_text(encoding="utf-8")
    assert guide == seed_module.guide_markdown(), "run scripts/seed_test_cases.py --guide"


def test_seeding_refuses_while_the_server_is_running(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(seed_module, "server_running", lambda port: True)
    monkeypatch.setattr("sys.argv", ["seed_test_cases.py"])
    assert seed_module.main() == 1
    assert "Stop it first" in capsys.readouterr().err
