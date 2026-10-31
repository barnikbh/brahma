"""Shared fixtures for the cases (U3) tests.

Every test gets its own temporary SQLite file. The real IBD pack (C1) and the real
audit trail (C2) are used; nothing touches ``./data``, a key or the network. Patients are
synthetic only.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

from brahma.cases import Case, CaseService, NewPatient, cs_connect
from brahma.knowledge import KnowledgeService
from brahma.knowledge.db import kg_connect
from brahma.platform.audit import AuditService

PROJECT_ROOT = Path(__file__).resolve().parents[2]
IBD_PACK = PROJECT_ROOT / "content" / "ibd.yaml"
SAFETY_PACK = Path(__file__).parent / "fixtures" / "safety_pack.yaml"
OWNER = "p-maya"
OTHER_OWNER = "p-urologist"


class FakeClock:
    """A settable clock (seconds) for the 45 s lock expiry."""

    def __init__(self, now: float = 1_000_000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def tmp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A fresh database path, also exported as BRAHMA_DB_PATH."""
    path = tmp_path / "brahma.db"
    monkeypatch.setenv("BRAHMA_DB_PATH", str(path))
    return path


@pytest.fixture
def conn(tmp_db: Path) -> Iterator[sqlite3.Connection]:
    """A connection holding the pf_ and cs_ tables."""
    connection = cs_connect(tmp_db)
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture
def knowledge(tmp_db: Path) -> Iterator[KnowledgeService]:
    """KnowledgeService with content/ibd.yaml and the inline safety pack loaded."""
    service = KnowledgeService(kg_connect(tmp_db))
    service.load_pack(IBD_PACK)
    service.load_pack(SAFETY_PACK)
    try:
        yield service
    finally:
        service.close()


@pytest.fixture
def audit(conn: sqlite3.Connection) -> AuditService:
    """The real C2 AuditService on the shared connection (seeds the demo profiles)."""
    return AuditService(conn)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def make_service(
    conn: sqlite3.Connection, knowledge: KnowledgeService, audit: AuditService, clock: FakeClock
) -> Callable[..., CaseService]:
    """Build a CaseService for a default pack (IBD unless a test asks for TSF)."""

    def _make(default_pack: str = "IBD") -> CaseService:
        return CaseService(conn, knowledge, default_pack=default_pack, clock=clock)

    return _make


@pytest.fixture
def cases(make_service: Callable[..., CaseService]) -> CaseService:
    """CaseService over the IBD pack."""
    return make_service()


@pytest.fixture
def safety_cases(make_service: Callable[..., CaseService]) -> CaseService:
    """CaseService over the inline TSF safety pack."""
    return make_service("TSF")


@pytest.fixture
def demo_patient() -> NewPatient:
    """Synthetic demo patient: 34-year-old woman, 58 kg, penicillin allergy, levothyroxine."""
    return NewPatient(
        synthetic_name="Demo Patient A (synthetic)",
        age=34,
        sex="female",
        weight_kg=58,
        pregnancy_status="not_pregnant",
        comorbidities=["hypothyroidism"],
        allergies=["penicillin"],
        current_medication=["levothyroxine"],
    )


@pytest.fixture
def demo_case(cases: CaseService, demo_patient: NewPatient) -> Case:
    return cases.create_case(demo_patient, OWNER)


@pytest.fixture
def audit_entries(conn: sqlite3.Connection) -> Callable[[str], list[dict[str, Any]]]:
    """Read a case's audit entries (kind and payload) in write order."""

    def _read(case_id: str) -> list[dict[str, Any]]:
        rows = conn.execute(
            "SELECT kind, profile_id, payload_json FROM pf_audit_entry WHERE case_id = ? "
            "ORDER BY created_at, rowid",
            (case_id,),
        )
        return [
            {"kind": r["kind"], "profileId": r["profile_id"], **json.loads(r["payload_json"])}
            for r in rows
        ]

    return _read
