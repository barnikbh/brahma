"""Shared fixtures for the grounded-agent (U4) tests.

Every test gets its own temporary SQLite file with the real IBD and urology packs (C1),
the real audit (C2), cases (C5) and model gateway (C4) on the recorded provider. The
recorded replies live in ``fixtures/recorded/<scenario>/<purpose>/default.json`` and are
synthetic, paraphrased from the packs' own nodes. Nothing touches the network, a key or
``./data``. The demo patient is synthetic: a 34-year-old woman, 58 kg (AC3.2.1).
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

from brahma.agent.db import ag_connect
from brahma.agent.engine import WalkEngine
from brahma.agent.logging import WalkLogger
from brahma.agent.models import WalkEvent, WalkRequest
from brahma.agent.repository import WalkRepository
from brahma.cases import Case, CaseService, NewPatient
from brahma.knowledge import KnowledgeService
from brahma.knowledge.db import kg_connect
from brahma.platform import ENV_VARS
from brahma.platform.audit import AuditService
from brahma.platform.errors import ModelTimeout, ModelUnavailable
from brahma.platform.models import ModelGateway, ModelRequest, ProviderConfig
from brahma.platform.models.adapters import AdapterResult, ProviderAdapter, RecordedAdapter
from brahma.platform.models.bucket import TokenBucket
from brahma.server.config import ENV_VARS as SERVER_ENV_VARS

PROJECT_ROOT = Path(__file__).resolve().parents[2]
IBD_PACK = PROJECT_ROOT / "content" / "ibd.yaml"
URO_PACK = PROJECT_ROOT / "content" / "urology.yaml"
RECORDED = Path(__file__).parent / "fixtures" / "recorded"
DOCTOR = "p-maya"
UROLOGIST = "p-urologist"
DEMO_TEXT = "34-year-old woman, bloody stool 6 months, Hb 10.2 g/dL, calprotectin 850 µg/g"
URO_TEXT = "45-year-old man with renal colic since yesterday, stone size 6 mm"
HEADACHE_TEXT = "29-year-old with headache with visual aura for 2 days"
FIRST_RESULTS = {"IBD-N20": "negative", "IBD-N21": "ulcerative colitis"}
SECOND_RESULTS = {"IBD-N22": "E3", "IBD-N23": "severe"}
DEMO_RESULTS = (FIRST_RESULTS, SECOND_RESULTS)


class FakeClock:
    """A settable clock (seconds) for the case lock."""

    def __init__(self, now: float = 1_000_000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


class ChainAdapter:
    """Recorded replies from the first scenario folder that has one (scenario, then demo)."""

    provider = "recorded"

    def __init__(self, adapters: list[ProviderAdapter]) -> None:
        self._adapters = adapters

    def call(self, request: ModelRequest, model: str, timeout: float) -> AdapterResult:
        for adapter in self._adapters[:-1]:
            try:
                return adapter.call(request, model, timeout)
            except ModelUnavailable:
                continue
        return self._adapters[-1].call(request, model, timeout)


class TimeoutAdapter:
    """Raises U2's ModelTimeout for requests containing ``match``, ``times`` times."""

    provider = "recorded"

    def __init__(self, inner: ProviderAdapter, match: str, times: int) -> None:
        self._inner = inner
        self._match = match
        self.remaining = times

    def call(self, request: ModelRequest, model: str, timeout: float) -> AdapterResult:
        asked = "\n".join(str(m["content"]) for m in request.messages)
        if self.remaining > 0 and self._match in asked:
            self.remaining -= 1
            raise ModelTimeout("recorded", retryable=True, reason="simulated timeout")
        return self._inner.call(request, model, timeout)


def recorded(scenario: str = "demo") -> ProviderAdapter:
    """The recorded adapter for a scenario, falling back to the demo replies."""
    chain: list[ProviderAdapter] = [RecordedAdapter(RECORDED / scenario)]
    if scenario != "demo":
        chain.append(RecordedAdapter(RECORDED / "demo"))
    return ChainAdapter(chain)


def make_gateway_for(conn: sqlite3.Connection, adapter: ProviderAdapter) -> ModelGateway:
    """A recorded-provider gateway with no throttling waits and no retry sleeps."""
    return ModelGateway(
        ProviderConfig(provider="recorded", model="recorded"),
        adapter,
        conn,
        bucket=TokenBucket(1000, capacity=1000),
        sleep=lambda _s: None,
    )


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Remove U2 and server variables so a local `.env` never leaks into a test."""
    for name in (*ENV_VARS, *SERVER_ENV_VARS):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("BRAHMA_MODEL_PROVIDER", "recorded")
    monkeypatch.setenv("BRAHMA_LOG_PATH", str(tmp_path / "brahma.log"))


@pytest.fixture
def tmp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A fresh database path, also exported as BRAHMA_DB_PATH."""
    path = tmp_path / "brahma.db"
    monkeypatch.setenv("BRAHMA_DB_PATH", str(path))
    return path


@pytest.fixture
def conn(tmp_db: Path) -> Iterator[sqlite3.Connection]:
    """A connection holding the pf_, cs_ and ag_ tables."""
    connection = ag_connect(tmp_db)
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture
def knowledge(tmp_db: Path) -> Iterator[KnowledgeService]:
    """KnowledgeService with content/ibd.yaml (IBD 1.0) and content/urology.yaml (URO 0.1)."""
    service = KnowledgeService(kg_connect(tmp_db))
    service.load_pack(IBD_PACK)
    service.load_pack(URO_PACK)
    try:
        yield service
    finally:
        service.close()


@pytest.fixture
def audit(conn: sqlite3.Connection) -> AuditService:
    """C2 on the shared connection (seeds the demo profiles)."""
    return AuditService(conn)


@pytest.fixture
def cases(
    conn: sqlite3.Connection, knowledge: KnowledgeService, audit: AuditService
) -> CaseService:
    """C5 over the IBD default pack with a fixed clock."""
    return CaseService(conn, knowledge, clock=FakeClock())


@pytest.fixture
def repo(conn: sqlite3.Connection) -> WalkRepository:
    return WalkRepository(conn)


@pytest.fixture
def log_path(tmp_path: Path) -> Path:
    return tmp_path / "brahma.log"


@pytest.fixture
def make_engine(
    conn: sqlite3.Connection,
    knowledge: KnowledgeService,
    cases: CaseService,
    audit: AuditService,
    repo: WalkRepository,
    log_path: Path,
) -> Callable[..., WalkEngine]:
    """Build a WalkEngine on a recorded scenario, or on a given adapter."""

    def _make(scenario: str = "demo", adapter: ProviderAdapter | None = None) -> WalkEngine:
        return WalkEngine(
            knowledge=knowledge,
            cases=cases,
            audit=audit,
            gateway=make_gateway_for(conn, adapter or recorded(scenario)),
            repo=repo,
            logger=WalkLogger(log_path),
        )

    return _make


@pytest.fixture
def engine(make_engine: Callable[..., WalkEngine]) -> WalkEngine:
    """The engine on the demo replies."""
    return make_engine()


@pytest.fixture
def demo_patient() -> NewPatient:
    """Synthetic demo patient: 34-year-old woman, 58 kg, no allergies."""
    return NewPatient(
        synthetic_name="Demo Patient A (synthetic)", age=34, sex="female", weight_kg=58
    )


@pytest.fixture
def demo_case(cases: CaseService, demo_patient: NewPatient) -> Case:
    return cases.create_case(demo_patient, DOCTOR)


@pytest.fixture
def uro_case(cases: CaseService) -> Case:
    patient = NewPatient(synthetic_name="Demo Patient U (synthetic)", age=45, sex="male")
    return cases.create_case(patient, UROLOGIST)


@pytest.fixture
def audit_rows(conn: sqlite3.Connection) -> Callable[[str], list[dict[str, Any]]]:
    """A case's audit entries (kind plus payload) in write order."""

    def _read(case_id: str) -> list[dict[str, Any]]:
        rows = conn.execute(
            "SELECT kind, pack_version, payload_json FROM pf_audit_entry WHERE case_id = ? "
            "ORDER BY created_at, rowid",
            (case_id,),
        )
        return [
            {"kind": r["kind"], "packVersion": r["pack_version"], **json.loads(r["payload_json"])}
            for r in rows
        ]

    return _read


# --- walk helpers ----------------------------------------------------------------------


def collect(
    engine: WalkEngine, case_id: str, profile: str = DOCTOR, **request: Any
) -> list[WalkEvent]:
    """Every event of one walk request."""
    return list(engine.events(case_id, WalkRequest.model_validate(request), profile))


def of_type(events: list[WalkEvent], kind: str) -> list[dict[str, Any]]:
    """The payloads of the events of one type."""
    return [e.payload for e in events if e.type == kind]


def confirmed_findings(form: dict[str, Any]) -> list[dict[str, Any]]:
    """The doctor confirms the extracted chips unchanged."""
    return [
        {
            "kind": f["findingKind"],
            "name": f["name"],
            "value": f["value"],
            "unit": f["unit"],
            "duration": f["duration"],
        }
        for f in form["fields"]
    ]


def walk_through(
    engine: WalkEngine,
    case_id: str,
    text: str = DEMO_TEXT,
    results: tuple[dict[str, str], ...] = DEMO_RESULTS,
    profile: str = DOCTOR,
) -> list[WalkEvent]:
    """Start, confirm the findings, then answer each needs-data form in turn."""
    events = collect(engine, case_id, profile, mode="start", text=text)
    form = of_type(events, "form")[0]
    walk_id = form["walkId"]
    step = collect(
        engine,
        case_id,
        profile,
        mode="continue",
        walkId=walk_id,
        formMessageId=form["messageId"],
        formValues={"findings": confirmed_findings(form)},
    )
    events += step
    for answers in results:
        forms = of_type(step, "form")
        if not forms:
            break
        step = collect(
            engine,
            case_id,
            profile,
            mode="continue",
            walkId=walk_id,
            formMessageId=forms[-1]["messageId"],
            formValues=answers,
        )
        events += step
    return events
