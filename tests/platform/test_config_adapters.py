"""Provider config, token bucket and adapters (BR3.1, NFR5.1, NFR8.3, NFR10.1)."""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import anthropic
import httpx
import httpx2
import pytest
import respx

from brahma.platform.errors import (
    ConfigError,
    ModelAuthError,
    ModelRateLimited,
    ModelTimeout,
    ModelUnavailable,
)
from brahma.platform.models import ModelGateway, ModelRequest, ProviderConfig
from brahma.platform.models.adapters import (
    ClaudeAdapter,
    LlamaHostedAdapter,
    MetaAdapter,
    RecordedAdapter,
    request_hash,
)
from brahma.platform.models.bucket import TokenBucket
from tests.platform.conftest import FAKE_BASE_URL

FAKE_KEY = "fake-key-for-tests-0001"


def _request(purpose: str = "extract", schema: dict[str, Any] | None = None) -> ModelRequest:
    return ModelRequest(
        purpose=purpose,  # type: ignore[arg-type]
        messages=[{"role": "user", "content": "Synthetic: calprotectin 450 µg/g"}],
        max_tokens=50,
        response_schema=schema,
    )


def test_https_is_required_and_values_never_shown() -> None:
    env = {
        "BRAHMA_MODEL_PROVIDER": "meta",
        "BRAHMA_MODEL_NAME": "Llama-4-Maverick",
        "META_API_KEY": FAKE_KEY,
        "BRAHMA_MODEL_BASE_URL": "http://insecure.test/v1",
    }
    with pytest.raises(ConfigError, match="https://") as caught:
        ProviderConfig.from_env(env)
    assert FAKE_KEY not in str(caught.value)
    assert "insecure.test" not in str(caught.value)


@pytest.mark.parametrize(
    ("env", "named"),
    [
        ({}, "BRAHMA_MODEL_PROVIDER"),
        ({"BRAHMA_MODEL_PROVIDER": "gpt"}, "BRAHMA_MODEL_PROVIDER"),
        ({"BRAHMA_MODEL_PROVIDER": "claude"}, "BRAHMA_MODEL_NAME"),
        ({"BRAHMA_MODEL_PROVIDER": "claude", "BRAHMA_MODEL_NAME": "m"}, "ANTHROPIC_API_KEY"),
        (
            {
                "BRAHMA_MODEL_PROVIDER": "llama_hosted",
                "BRAHMA_MODEL_NAME": "m",
                "LLAMA_API_KEY": "",
            },
            "LLAMA_API_KEY",
        ),
        (
            {
                "BRAHMA_MODEL_PROVIDER": "meta",
                "BRAHMA_MODEL_NAME": "m",
                "META_API_KEY": FAKE_KEY,
                "BRAHMA_MODEL_RPM": "lots",
            },
            "BRAHMA_MODEL_RPM",
        ),
    ],
)
def test_missing_or_bad_setting_names_only_the_variable(env: dict[str, str], named: str) -> None:
    with pytest.raises(ConfigError, match=named) as caught:
        ProviderConfig.from_env(env)
    assert FAKE_KEY not in str(caught.value)


def test_valid_hosted_config_uses_defaults() -> None:
    config = ProviderConfig.from_env(
        {
            "BRAHMA_MODEL_PROVIDER": "llama_hosted",
            "BRAHMA_MODEL_NAME": "llama-3.3-70b",
            "LLAMA_API_KEY": FAKE_KEY,
            "BRAHMA_MODEL_TIMEOUT_S": "20",
        }
    )
    assert config.base_url == "https://api.groq.com/openai/v1"
    assert (config.requests_per_minute, config.timeout_seconds) == (30, 20)
    assert config.api_key is not None and config.api_key.get_secret_value() == FAKE_KEY


def test_recorded_provider_starts_with_an_empty_environment(
    conn: sqlite3.Connection, recorded_dir: Path
) -> None:
    gateway = ModelGateway.from_env(
        conn, {"BRAHMA_MODEL_PROVIDER": "recorded"}, recorded_dir=recorded_dir
    )

    response = gateway.complete(_request())

    assert gateway.current().model_dump() == {"provider": "recorded", "model": "recorded"}
    assert "µg/g" in response.text
    assert (response.input_tokens, response.output_tokens) == (120, 24)


def test_recorded_adapter_prefers_the_hashed_fixture(tmp_path: Path) -> None:
    request = _request()
    folder = tmp_path / "extract"
    folder.mkdir()
    (folder / "default.json").write_text(json.dumps({"text": "default"}), encoding="utf-8")
    (folder / f"{request_hash(request)}.json").write_text(
        json.dumps({"text": "exact"}), encoding="utf-8"
    )
    adapter = RecordedAdapter(tmp_path)

    assert adapter.call(request, "recorded", 5).text == "exact"
    assert adapter.call(_request(schema={"type": "object"}), "recorded", 5).text == "default"
    with pytest.raises(ModelUnavailable) as caught:
        adapter.call(_request(purpose="draft"), "recorded", 5)
    assert caught.value.retryable is False


def test_concurrent_token_takes_respect_the_rate() -> None:
    bucket = TokenBucket(600, capacity=1)  # 10 per second, no burst
    started = time.perf_counter()
    threads = [threading.Thread(target=bucket.take) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    elapsed = time.perf_counter() - started

    assert elapsed >= 0.45  # 5 waits of 0.1 s after the first free token
    with pytest.raises(ValueError):
        TokenBucket(0)


def test_openai_compatible_adapter_maps_odd_replies(fake_http: respx.MockRouter) -> None:
    route = fake_http.post("/chat/completions")
    adapter = MetaAdapter(FAKE_BASE_URL, FAKE_KEY, httpx.Client())

    route.mock(return_value=httpx.Response(200, json={"choices": []}))
    with pytest.raises(ModelUnavailable, match="malformed"):
        adapter.call(_request(), "m", 5)
    route.mock(return_value=httpx.Response(400, json={"error": "bad"}))
    with pytest.raises(ModelUnavailable) as caught:
        adapter.call(_request(), "m", 5)
    assert caught.value.retryable is False
    route.mock(side_effect=httpx.ConnectError("refused"))
    with pytest.raises(ModelUnavailable) as connection:
        adapter.call(_request(), "m", 5)
    assert connection.value.retryable is True


def test_meta_adapter_leaves_room_for_reasoning(fake_http: respx.MockRouter) -> None:
    route = fake_http.post("/chat/completions")
    route.mock(return_value=httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]}))
    request = _request()
    MetaAdapter(FAKE_BASE_URL, FAKE_KEY, httpx.Client()).call(request, "m", 5)
    sent = json.loads(route.calls.last.request.content)
    assert sent["reasoning_effort"] == "low"
    assert sent["max_tokens"] == request.max_tokens + MetaAdapter.REASONING_ALLOWANCE

    LlamaHostedAdapter(FAKE_BASE_URL, FAKE_KEY, httpx.Client()).call(request, "m", 5)
    sent = json.loads(route.calls.last.request.content)
    assert "reasoning_effort" not in sent
    assert sent["max_tokens"] == request.max_tokens


class _FakeMessages:
    def __init__(self, outcomes: list[Any]) -> None:
        self.outcomes = outcomes
        self.calls: list[dict[str, Any]] = []

    def create(self, **options: Any) -> Any:
        self.calls.append(options)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _status_error(cls: type[anthropic.APIStatusError], status: int, **headers: str) -> Any:
    request = httpx2.Request("POST", "https://claude.test/v1/messages")
    response = httpx2.Response(status, headers=headers, request=request)
    return cls(f"echo {FAKE_KEY}", response=response, body=None)


def test_claude_adapter_with_a_fake_client() -> None:
    reply = SimpleNamespace(
        content=[SimpleNamespace(type="text", text='{"label": "UC"}')],
        usage=SimpleNamespace(input_tokens=11, output_tokens=7),
    )
    request = httpx2.Request("POST", "https://claude.test/v1/messages")
    messages = _FakeMessages(
        [
            reply,
            _status_error(anthropic.RateLimitError, 429, **{"retry-after": "2"}),
            _status_error(anthropic.AuthenticationError, 401),
            anthropic.APITimeoutError(request=request),
            anthropic.APIConnectionError(request=request),
        ]
    )
    adapter = ClaudeAdapter(client=SimpleNamespace(messages=messages))
    schema = {"type": "object", "properties": {"label": {"type": "string"}}}

    result = adapter.call(_request(schema=schema), "claude-test", 30)
    assert (result.text, result.input_tokens, result.output_tokens) == ('{"label": "UC"}', 11, 7)
    assert "JSON" in messages.calls[0]["system"]
    assert all(m["role"] != "system" for m in messages.calls[0]["messages"])
    with pytest.raises(ModelRateLimited) as limited:
        adapter.call(_request(), "claude-test", 30)
    assert limited.value.retry_after == 2.0
    with pytest.raises(ModelAuthError) as auth:
        adapter.call(_request(), "claude-test", 30)
    assert FAKE_KEY not in str(auth.value)
    with pytest.raises(ModelTimeout):
        adapter.call(_request(), "claude-test", 30)
    with pytest.raises(ModelUnavailable):
        adapter.call(_request(), "claude-test", 30)
