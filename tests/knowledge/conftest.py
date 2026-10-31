"""Shared fixtures for the knowledge-graph tests.

Every test gets its own temporary SQLite file through ``tmp_db``; nothing touches
``./data`` or the network.
"""

from __future__ import annotations

import copy
import sqlite3
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml

from brahma.knowledge.db import BUSY_TIMEOUT_MS, kg_connect

FIXTURES = Path(__file__).parent / "fixtures"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTENT = PROJECT_ROOT / "content"


@pytest.fixture
def tmp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A fresh database path, also exported as BRAHMA_DB_PATH."""
    path = tmp_path / "brahma.db"
    monkeypatch.setenv("BRAHMA_DB_PATH", str(path))
    return path


@pytest.fixture
def connect(tmp_db: Path) -> Iterator[Callable[..., sqlite3.Connection]]:
    """Open connections to the test database; all are closed when the test ends."""
    opened: list[sqlite3.Connection] = []

    def _connect(busy_timeout_ms: int = BUSY_TIMEOUT_MS) -> sqlite3.Connection:
        conn = kg_connect(tmp_db, busy_timeout_ms=busy_timeout_ms)
        opened.append(conn)
        return conn

    yield _connect
    for conn in opened:
        conn.close()


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def minimal_pack_path() -> Path:
    return FIXTURES / "minimal.yaml"


@pytest.fixture
def minimal_pack() -> dict[str, Any]:
    """The minimal valid pack as a dict; each test gets its own deep copy."""
    with (FIXTURES / "minimal.yaml").open(encoding="utf-8") as handle:
        data: dict[str, Any] = yaml.safe_load(handle)
    return copy.deepcopy(data)


@pytest.fixture
def write_pack(tmp_path: Path) -> Callable[[dict[str, Any], str], Path]:
    """Write a pack dict to a YAML file in the test's temp folder and return the path."""

    def _write(data: dict[str, Any], name: str = "pack.yaml") -> Path:
        path = tmp_path / name
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        return path

    return _write


@pytest.fixture
def service(tmp_db: Path) -> Iterator[Any]:
    """A KnowledgeService on the temporary database."""
    from brahma.knowledge import KnowledgeService

    svc = KnowledgeService.open(tmp_db)
    try:
        yield svc
    finally:
        svc.close()
