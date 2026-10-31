"""ModelGateway: retries, structured output and key-free logging (BR3.2-BR3.4, NFR1.1, NFR6.1)."""

from __future__ import annotations

import json
import logging
import sqlite3
import statistics
import time
from pathlib import Path
from typing import Any, Literal

import httpx
import pytest
import respx
from pydantic import BaseModel, SecretStr

from brahma.platform.errors import (
    ModelAuthError,
    ModelRateLimited,
    ModelUnavailable,
)
from brahma.platform.models import ModelGateway, ModelRequest, ProviderConfig
from brahma.platform.models.adapters import MetaAdapter, RecordedAdapter
from brahma.platform.models.bucket import TokenBucket
from brahma.platform.models.gateway import LOGGER_NAME
from tests.platform.conftest import FAKE_BASE_URL

FAKE_KEY = "fake-key-for-tests-0001"
PROMPT = "SYNTHETIC-PROMPT-TEXT calprotectin 450"
REPLY = "SYNTHETIC-REPLY-TEXT"
SCHEMA = {
    "type": "object",
    "properties": {"label": {"type": "string"}, "score": {"type": "integer"}},
    "required": ["label"],
}


def _ok(text: str = REPLY) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [{"message": {"content": text}}],
            "usage": {"prompt_tokens": 9, "completion_tokens": 4},
        },
    )


def _request(schema: dict[str, Any] | None = None) -> ModelRequest:
    return ModelRequest(
        purpose="extract",
        messages=[{"role": "user", "content": PROMPT}],
        max_tokens=50,
        response_schema=schema,
    )


class _Gateway:
    """A Meta gateway against the fake provider that records sleeps instead of waiting."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.sleeps: list[float] = []
        config = ProviderConfig(
            provider="meta",
            model="Llama-test",
            api_key_env="META_API_KEY",
            api_key=SecretStr(FAKE_KEY),
            base_url=FAKE_BASE_URL,
            requests_per_minute=1000,
        )
        adapter = MetaAdapter(FAKE_BASE_URL, FAKE_KEY, httpx.Client())
        self.gateway = ModelGateway(config, adapter, conn, sleep=self.sleeps.append)


@pytest.fixture
def gw(conn: sqlite3.Connection) -> _Gateway:
    return _Gateway(conn)


@pytest.fixture
def route(fake_http: respx.MockRouter) -> respx.Route:
    return fake_http.post("/chat/completions")


def _call_log(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return [dict(r) for r in conn.execute("SELECT * FROM pf_model_call_log ORDER BY rowid")]


def test_timeout_then_success(gw: _Gateway, route: respx.Route, conn: sqlite3.Connection) -> None:
    route.side_effect = [httpx.ReadTimeout("slow"), _ok()]

    response = gw.gateway.complete(_request())

    assert response.text == REPLY
    assert (response.provider, response.input_tokens, response.output_tokens) == ("meta", 9, 4)
    assert gw.sleeps == [1.0]
    assert _call_log(conn)[0]["attempts"] == 2


def test_429_then_success_honours_retry_after(gw: _Gateway, route: respx.Route) -> None:
    route.side_effect = [httpx.Response(429, headers={"Retry-After": "2"}), _ok()]

    assert gw.gateway.complete(_request()).text == REPLY
    assert gw.sleeps == [2.0]


def test_three_500s_raise_model_unavailable(
    gw: _Gateway, route: respx.Route, conn: sqlite3.Connection
) -> None:
    route.mock(return_value=httpx.Response(500))

    with pytest.raises(ModelUnavailable) as caught:
        gw.gateway.complete(_request())

    assert (caught.value.provider, caught.value.retryable, caught.value.status) == (
        "meta",
        True,
        500,
    )
    assert route.call_count == 3
    assert gw.sleeps == [1.0, 3.0]
    row = _call_log(conn)[0]
    assert (row["attempts"], row["error"]) == (3, "ModelUnavailable 500")


def test_401_is_not_retried(gw: _Gateway, route: respx.Route) -> None:
    route.mock(return_value=httpx.Response(401))

    with pytest.raises(ModelAuthError) as caught:
        gw.gateway.complete(_request())

    assert caught.value.retryable is False
    assert route.call_count == 1
    assert gw.sleeps == []


def test_long_retry_after_raises_without_waiting(gw: _Gateway, route: respx.Route) -> None:
    route.mock(return_value=httpx.Response(429, headers={"Retry-After": "30"}))

    with pytest.raises(ModelRateLimited) as caught:
        gw.gateway.complete(_request())

    assert caught.value.retryable is True
    assert caught.value.retry_after == 30.0
    assert route.call_count == 1
    assert gw.sleeps == []


def test_invalid_json_then_valid_json_succeeds(gw: _Gateway, route: respx.Route) -> None:
    route.side_effect = [_ok("not json at all"), _ok('Here it is: {"label": "UC", "score": 2}')]

    response = gw.gateway.complete(_request(SCHEMA))

    assert response.parsed == {"label": "UC", "score": 2}
    assert gw.sleeps == [1.0]


def test_three_invalid_outputs_raise(
    gw: _Gateway, route: respx.Route, conn: sqlite3.Connection
) -> None:
    route.side_effect = [_ok("{}"), _ok('{"label": "UC", "score": "high"}'), _ok("[1, 2]")]

    with pytest.raises(ModelUnavailable, match="invalid structured output"):
        gw.gateway.complete(_request(SCHEMA))

    assert route.call_count == 3
    assert _call_log(conn)[0]["error"] == "ModelUnavailable"


class _Severity(BaseModel):
    level: Literal["mild", "moderate", "severe"]
    score: float


class _Extraction(BaseModel):
    findings: list[str]
    severity: _Severity
    note: str | None = None


def test_pydantic_generated_schema_is_validated(gw: _Gateway, route: respx.Route) -> None:
    schema = _Extraction.model_json_schema()
    good = {"findings": ["bloody stool"], "severity": {"level": "moderate", "score": 6}}
    route.side_effect = [
        _ok(json.dumps({**good, "severity": {"level": "awful"}})),
        _ok(json.dumps(good)),
    ]

    response = gw.gateway.complete(_request(schema))

    assert response.parsed is not None
    assert response.parsed["severity"] == {"level": "moderate", "score": 6}
    assert response.parsed["note"] is None


def test_logs_and_call_log_hold_no_key_or_text(
    gw: _Gateway,
    route: respx.Route,
    conn: sqlite3.Connection,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)
    route.side_effect = [
        _ok(),
        httpx.Response(401, json={"error": f"bad key {FAKE_KEY}", "echo": PROMPT}),
    ]

    gw.gateway.complete(_request())
    with pytest.raises(ModelAuthError) as caught:
        gw.gateway.complete(_request())

    stored = json.dumps(_call_log(conn))
    for leaked in (FAKE_KEY, PROMPT, REPLY, "bad key"):
        assert leaked not in caplog.text
        assert leaked not in stored
        assert leaked not in str(caught.value)
    assert '"error": "ModelAuthError 401"' in caplog.text


def test_one_log_line_and_one_row_per_call(
    gw: _Gateway,
    route: respx.Route,
    conn: sqlite3.Connection,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)
    route.side_effect = [httpx.Response(503), _ok(), _ok()]

    gw.gateway.complete(_request())
    gw.gateway.complete(_request())

    lines = [json.loads(r.getMessage()) for r in caplog.records if r.name == LOGGER_NAME]
    assert [line["attempts"] for line in lines] == [2, 1]
    assert {line["purpose"] for line in lines} == {"extract"}
    rows = _call_log(conn)
    assert len(rows) == 2
    assert all(r["error"] is None and r["latency_ms"] >= 0 for r in rows)


@pytest.mark.timing
def test_recorded_provider_overhead_is_under_20_ms(
    conn: sqlite3.Connection, recorded_dir: Path
) -> None:
    config = ProviderConfig(provider="recorded", model="recorded", requests_per_minute=1000)
    gateway = ModelGateway(
        config, RecordedAdapter(recorded_dir), conn, bucket=TokenBucket(1000, capacity=1000)
    )
    durations = []
    for _ in range(30):
        started = time.perf_counter()
        gateway.complete(_request())
        durations.append((time.perf_counter() - started) * 1000)

    assert statistics.median(durations) < 20
