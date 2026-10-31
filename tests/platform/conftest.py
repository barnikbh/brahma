"""Shared fixtures for the platform (U2) tests.

Every test gets its own temporary SQLite file through ``tmp_db``. Provider HTTP is faked
with respx and the recorded provider reads ``fixtures/recorded/``; nothing touches
``./data``, a real key or the network.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
import respx

from brahma.platform import ENV_VARS

RECORDED_DIR = Path(__file__).parent / "fixtures" / "recorded"
FAKE_BASE_URL = "https://fake-provider.test/v1"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove every U2 variable so a developer's local `.env` never leaks into a test."""
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def tmp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A fresh database path, also exported as BRAHMA_DB_PATH."""
    path = tmp_path / "brahma.db"
    monkeypatch.setenv("BRAHMA_DB_PATH", str(path))
    return path


@pytest.fixture
def conn(tmp_db: Path) -> Iterator[sqlite3.Connection]:
    """A U2 connection to the temporary database, closed when the test ends."""
    from brahma.platform.db import pf_connect

    connection = pf_connect(tmp_db)
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture
def recorded_dir() -> Path:
    """The recorded-provider fixture directory (one folder per purpose)."""
    return RECORDED_DIR


@pytest.fixture
def fake_http() -> Iterator[respx.MockRouter]:
    """A respx router for the fake provider; any unmatched request fails the test."""
    with respx.mock(base_url=FAKE_BASE_URL, assert_all_called=False) as router:
        yield router
