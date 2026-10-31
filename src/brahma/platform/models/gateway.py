"""``ModelGateway``: contract C4 (BR3.1-BR3.4, NFR6.1, NFR8.1, NFR8.2, NFR11.1).

The only place in Brahma that retries a model call. Each call takes a throttle token,
runs with the configured timeout and is retried at most twice (1 s, then 3 s, or the
provider's Retry-After up to 10 s). Every call, successful or not, writes one JSON log
line and one ``pf_model_call_log`` row holding metadata only: never prompt or response
text, never a key, and as error only the error class plus the HTTP status.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from pydantic import ValidationError

from brahma.platform.base import new_id, utc_now
from brahma.platform.db import transaction
from brahma.platform.errors import ModelError, ModelRateLimited, ModelUnavailable
from brahma.platform.models.adapters import (
    DEFAULT_RECORDED_DIR,
    AdapterResult,
    ProviderAdapter,
    build_adapter,
)
from brahma.platform.models.bucket import TokenBucket
from brahma.platform.models.config import ProviderConfig
from brahma.platform.models.schemas import CurrentModel, ModelRequest, ModelResponse
from brahma.platform.models.structured import first_json_object, model_for_schema

MAX_ATTEMPTS = 3
BACKOFF_S = (1.0, 3.0)
MAX_RETRY_AFTER_S = 10.0
LOGGER_NAME = "brahma.platform.models"

_log = logging.getLogger(LOGGER_NAME)


class _InvalidOutput(Exception):
    """The reply did not hold a JSON object matching the request's schema."""


@dataclass
class _CallState:
    started: float
    attempts: int = 0
    throttle_s: float = 0.0
    input_tokens: int | None = None
    output_tokens: int | None = None
    error: BaseException | None = None


class ModelGateway:
    """One configured provider, throttled, with bounded retries and call logging."""

    def __init__(
        self,
        config: ProviderConfig,
        adapter: ProviderAdapter,
        conn: sqlite3.Connection,
        *,
        bucket: TokenBucket | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self._config = config
        self._adapter = adapter
        self._conn = conn
        self._bucket = bucket or TokenBucket(config.requests_per_minute)
        self._sleep = sleep
        self._clock = clock

    @classmethod
    def from_env(
        cls,
        conn: sqlite3.Connection,
        env: Mapping[str, str] | None = None,
        *,
        http_client: httpx.Client | None = None,
        recorded_dir: Path = DEFAULT_RECORDED_DIR,
    ) -> ModelGateway:
        """Build from the environment (BR3.1). Raises ConfigError naming any missing variable."""
        config = ProviderConfig.from_env(env)
        adapter = build_adapter(config, http_client=http_client, recorded_dir=recorded_dir)
        return cls(config, adapter, conn)

    def current(self) -> CurrentModel:
        """The active provider and model."""
        return CurrentModel(provider=self._config.provider, model=self._config.model)

    def complete(self, request: ModelRequest) -> ModelResponse:
        """Run one completion with throttling, timeout, retries and schema validation.

        Raises ModelTimeout, ModelRateLimited, ModelAuthError or ModelUnavailable (each
        with ``provider`` and ``retryable``) once retries are used up or not allowed.
        """
        state = _CallState(started=self._clock())
        try:
            return self._run(request, state)
        except BaseException as exc:
            state.error = exc
            raise
        finally:
            self._record(request, state)

    def _run(self, request: ModelRequest, state: _CallState) -> ModelResponse:
        provider = self._config.provider
        for attempt in range(1, MAX_ATTEMPTS + 1):
            state.attempts = attempt
            state.throttle_s += self._bucket.take()
            try:
                result = self._adapter.call(
                    request, self._config.model, float(self._config.timeout_seconds)
                )
                state.input_tokens, state.output_tokens = result.input_tokens, result.output_tokens
                return self._response(request, result, state)
            except ModelError as exc:
                if not exc.retryable or attempt == MAX_ATTEMPTS:
                    raise
                self._sleep(self._backoff(attempt, exc))
            except _InvalidOutput:
                if attempt == MAX_ATTEMPTS:
                    raise ModelUnavailable(
                        provider, retryable=True, reason="invalid structured output"
                    ) from None
                self._sleep(BACKOFF_S[attempt - 1])
        raise AssertionError("unreachable: the loop returns or raises")  # pragma: no cover

    def _backoff(self, attempt: int, exc: ModelError) -> float:
        delay = BACKOFF_S[attempt - 1]
        if exc.retry_after is None:
            return delay
        if exc.retry_after > MAX_RETRY_AFTER_S:
            raise ModelRateLimited(
                exc.provider,
                retryable=True,
                status=exc.status,
                reason=f"provider asked to wait {exc.retry_after:.0f} s",
                retry_after=exc.retry_after,
            ) from None
        return max(delay, exc.retry_after)

    def _response(
        self, request: ModelRequest, result: AdapterResult, state: _CallState
    ) -> ModelResponse:
        parsed = self._validate(request, result.text)
        return ModelResponse(
            text=result.text,
            parsed=parsed,
            provider=self._config.provider,
            model=self._config.model,
            latency_ms=self._latency_ms(state),
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )

    @staticmethod
    def _validate(request: ModelRequest, text: str) -> dict[str, Any] | None:
        if request.response_schema is None:
            return None
        candidate = first_json_object(text)
        if candidate is None:
            raise _InvalidOutput
        try:
            model = model_for_schema(request.response_schema)
            return model.model_validate(candidate).model_dump(by_alias=True)
        except ValidationError:
            raise _InvalidOutput from None

    def _latency_ms(self, state: _CallState) -> int:
        elapsed = self._clock() - state.started - state.throttle_s
        return max(0, round(elapsed * 1000))

    def _record(self, request: ModelRequest, state: _CallState) -> None:
        error = state.error
        if error is None:
            label = None
        elif isinstance(error, ModelError):
            label = error.log_label()
        else:
            label = type(error).__name__
        meta: dict[str, Any] = {
            "event": "model_call",
            "callId": new_id("mc"),
            "provider": self._config.provider,
            "model": self._config.model,
            "purpose": request.purpose,
            "latencyMs": self._latency_ms(state),
            "inputTokens": state.input_tokens,
            "outputTokens": state.output_tokens,
            "attempts": max(1, state.attempts),
            "error": label,
        }
        _log.info(json.dumps(meta))
        self._insert_call_log(meta)

    def _insert_call_log(self, meta: dict[str, Any]) -> None:
        try:
            with transaction(self._conn):
                self._conn.execute(
                    "INSERT INTO pf_model_call_log (call_id, provider, model, purpose, "
                    "latency_ms, input_tokens, output_tokens, attempts, error, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        meta["callId"],
                        meta["provider"],
                        meta["model"],
                        meta["purpose"],
                        meta["latencyMs"],
                        meta["inputTokens"],
                        meta["outputTokens"],
                        meta["attempts"],
                        meta["error"],
                        utc_now(),
                    ),
                )
        except sqlite3.Error as exc:
            # Never mask the call's own result or error; the log line above still holds it.
            _log.error("model call log write failed: %s", type(exc).__name__)
