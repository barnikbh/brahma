"""Shared fixtures for the knowledge-updates (U5) tests.

Every test gets its own temporary SQLite file with the real IBD pack (C1), the real audit
and identity services (C2, C3) and the recorded model provider (C4). DNS goes through a
fake resolver and HTTP through respx, so nothing touches the network, a key or ``./data``.
Source pages are short synthetic HTML written for these tests, never guideline text.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from brahma.knowledge import KnowledgeService
from brahma.knowledge.db import kg_connect
from brahma.platform import ENV_VARS
from brahma.platform.audit import AuditService
from brahma.platform.identity import IdentityService
from brahma.platform.models import ModelGateway, ProviderConfig
from brahma.platform.models.adapters import RecordedAdapter
from brahma.platform.models.bucket import TokenBucket
from brahma.updates.check import ENV_HOURS
from brahma.updates.db import up_connect
from brahma.updates.fetch import SafeFetcher
from brahma.updates.service import UpdateService

PROJECT_ROOT = Path(__file__).resolve().parents[2]
IBD_PACK = PROJECT_ROOT / "content" / "ibd.yaml"
RECORDED_DIR = Path(__file__).parent / "fixtures" / "recorded"
DOCTOR = "p-maya"
REVIEWER = "p-reviewer"
PUBLIC_IP = "93.184.216.34"
SOURCE_URL = "https://guidelines.example.org/synthetic/colitis-update"

# Synthetic test page: made-up wording, not taken from any guideline.
SYNTHETIC_PAGE = """<html><head><title>Synthetic colitis note</title>
<style>p {color: red}</style><script>alert("ignored")</script></head>
<body><h1>Synthetic review note</h1>
<p>This made up page exists only for automated tests of the Brahma update flow and it
describes no real clinical guidance of any kind whatsoever for any patient at all today.</p>
<p>Colonic disease in this invented note is described as sparing the small bowel.</p>
</body></html>"""


class FakeResolver:
    """Maps host names to addresses; unknown hosts resolve to a public test address."""

    def __init__(self) -> None:
        self.hosts: dict[str, list[str]] = {}
        self.calls: list[str] = []

    def __call__(self, host: str, port: int) -> list[str]:
        self.calls.append(host)
        return self.hosts.get(host, [PUBLIC_IP])


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove the U2 and U5 variables so a local `.env` never leaks into a test."""
    for name in (*ENV_VARS, ENV_HOURS):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("BRAHMA_MODEL_PROVIDER", "recorded")


@pytest.fixture
def tmp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A fresh database path, also exported as BRAHMA_DB_PATH."""
    path = tmp_path / "brahma.db"
    monkeypatch.setenv("BRAHMA_DB_PATH", str(path))
    return path


@pytest.fixture
def conn(tmp_db: Path) -> Iterator[sqlite3.Connection]:
    """A connection holding the pf_ and up_ tables."""
    connection = up_connect(tmp_db)
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture
def knowledge(tmp_db: Path) -> Iterator[KnowledgeService]:
    """KnowledgeService with content/ibd.yaml loaded as IBD 1.1."""
    service = KnowledgeService(kg_connect(tmp_db))
    service.load_pack(IBD_PACK)
    try:
        yield service
    finally:
        service.close()


@pytest.fixture
def identity(conn: sqlite3.Connection) -> IdentityService:
    """C3 on the shared connection; seeds the demo doctor and the clinical reviewer."""
    return IdentityService(conn)


@pytest.fixture
def audit(conn: sqlite3.Connection) -> AuditService:
    """C2 on the shared connection."""
    return AuditService(conn)


@pytest.fixture
def resolver() -> FakeResolver:
    return FakeResolver()


@pytest.fixture
def http() -> Iterator[respx.MockRouter]:
    """A respx router; any request it does not match fails the test."""
    with respx.mock(assert_all_called=False) as router:
        yield router


@pytest.fixture
def fetcher(resolver: FakeResolver, http: respx.MockRouter) -> SafeFetcher:
    return SafeFetcher(httpx.Client(), resolver)


@pytest.fixture
def make_gateway(conn: sqlite3.Connection) -> Callable[[Path], ModelGateway]:
    """A recorded-provider gateway reading ``<dir>/draft_proposal/``; no sleeps."""

    def _make(recorded_dir: Path = RECORDED_DIR) -> ModelGateway:
        config = ProviderConfig(provider="recorded", model="recorded")
        return ModelGateway(
            config,
            RecordedAdapter(recorded_dir),
            conn,
            bucket=TokenBucket(1000, capacity=1000),
            sleep=lambda _s: None,
        )

    return _make


@pytest.fixture
def write_draft(tmp_path: Path) -> Callable[[dict[str, Any]], Path]:
    """Write a recorded ``draft_proposal`` reply to a temp folder and return the folder."""

    def _write(reply: dict[str, Any]) -> Path:
        folder = tmp_path / "recorded"
        (folder / "draft_proposal").mkdir(parents=True, exist_ok=True)
        fixture = {"text": json.dumps(reply), "inputTokens": 1, "outputTokens": 1}
        (folder / "draft_proposal" / "default.json").write_text(json.dumps(fixture), "utf-8")
        return folder

    return _write


@pytest.fixture
def make_service(
    conn: sqlite3.Connection,
    knowledge: KnowledgeService,
    identity: IdentityService,
    fetcher: SafeFetcher,
    make_gateway: Callable[[Path], ModelGateway],
) -> Callable[..., UpdateService]:
    def _make(recorded_dir: Path = RECORDED_DIR) -> UpdateService:
        return UpdateService(
            conn, knowledge, identity, fetcher=fetcher, gateway=make_gateway(recorded_dir)
        )

    return _make


@pytest.fixture
def updates(make_service: Callable[..., UpdateService]) -> UpdateService:
    """UpdateService over the IBD pack with the shipped recorded draft."""
    return make_service()


@pytest.fixture
def page(http: respx.MockRouter) -> Callable[..., respx.Route]:
    """Serve HTML at a URL through respx."""

    def _page(url: str = SOURCE_URL, html: str = SYNTHETIC_PAGE) -> respx.Route:
        return http.get(url).mock(
            return_value=httpx.Response(200, text=html, headers={"content-type": "text/html"})
        )

    return _page


@pytest.fixture
def audit_kinds(conn: sqlite3.Connection) -> Callable[[], list[dict[str, Any]]]:
    """Proposal audit rows (kind, profile, pack version, payload) in write order."""

    def _read() -> list[dict[str, Any]]:
        rows = conn.execute(
            "SELECT kind, profile_id, pack_version, payload_json FROM pf_audit_entry "
            "WHERE kind LIKE 'proposal_%' ORDER BY created_at, rowid"
        )
        return [
            {
                "kind": r["kind"],
                "profileId": r["profile_id"],
                "packVersion": r["pack_version"],
                **json.loads(r["payload_json"]),
            }
            for r in rows
        ]

    return _read
