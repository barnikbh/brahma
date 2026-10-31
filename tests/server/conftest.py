"""Shared fixtures for the backend server (U4) tests.

The app is built by ``create_app`` on a temporary SQLite file: start-up loads the real
packs from ``content/`` and seeds the demo profiles. The model gateway uses the recorded
demo replies from ``tests/agent/fixtures/recorded``. The session secret is random per
test. Nothing touches the network, a key or ``./data``.
"""

from __future__ import annotations

import json
import secrets
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from brahma.server.app import create_app
from brahma.server.config import ServerConfig
from brahma.server.services import Services
from tests.agent.conftest import (
    DOCTOR,
    PROJECT_ROOT,
    clean_env,  # noqa: F401 - autouse fixture shared with the agent tests
    make_gateway_for,
    recorded,
)

TAB = "tab-1"


@pytest.fixture
def config(tmp_path: Path) -> ServerConfig:
    return ServerConfig(
        session_secret=secrets.token_urlsafe(32),
        log_path=tmp_path / "brahma.log",
        db_path=tmp_path / "brahma.db",
        content_dir=PROJECT_ROOT / "content",
    )


@pytest.fixture
def app(config: ServerConfig) -> FastAPI:
    def gateway(conn: sqlite3.Connection) -> Any:
        return make_gateway_for(conn, recorded("demo"))

    return create_app(config, gateway_factory=gateway)


@pytest.fixture
def services(app: FastAPI) -> Services:
    shared: Services = app.state.services
    return shared


@pytest.fixture
def anon(app: FastAPI) -> Iterator[TestClient]:
    """A client that has not signed in."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    """A client signed in as the demo doctor, with the disclaimer accepted."""
    with TestClient(app) as signed_in:
        assert signed_in.post("/api/session", json={"profileId": DOCTOR}).status_code == 200
        assert signed_in.post("/api/disclaimer").status_code == 200
        yield signed_in


def sse(text: str) -> list[tuple[str, dict[str, Any]]]:
    """Parse a text/event-stream body into (event, data) pairs."""
    events: list[tuple[str, dict[str, Any]]] = []
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
        events.append((lines["event"], json.loads(lines["data"])))
    return events


def new_case(client: TestClient) -> str:
    """Create the synthetic demo patient and take the case lock in this tab."""
    body = {
        "syntheticName": "Demo Patient A (synthetic)",
        "age": 34,
        "sex": "female",
        "weightKg": 58,
    }
    response = client.post("/api/patients", json=body)
    assert response.status_code == 201, response.text
    case_id: str = response.json()["case"]["caseId"]
    assert client.post(f"/api/cases/{case_id}/lock", json={"tabId": TAB}).json() == {
        "state": "held"
    }
    return case_id
