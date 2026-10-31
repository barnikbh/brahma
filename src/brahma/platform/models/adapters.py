"""Provider adapters behind the gateway (FR14.1, NFR8.1, NFR10.1).

Each adapter makes exactly one call and maps every failure to a typed ``ModelError``.
Adapters never retry (the gateway does) and never put a key, response body or prompt
text into an error. Structured output: the Meta API's JSON-schema mode is an open
question (contract C4), so every adapter asks for JSON with an instruction and the
gateway parses and validates the reply (BR3.4).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import anthropic
import httpx

from brahma.platform.errors import (
    ModelAuthError,
    ModelError,
    ModelRateLimited,
    ModelTimeout,
    ModelUnavailable,
)
from brahma.platform.models.config import ProviderConfig
from brahma.platform.models.schemas import ModelRequest

DEFAULT_RECORDED_DIR = Path("tests/platform/fixtures/recorded")


@dataclass(frozen=True)
class AdapterResult:
    """The provider's text reply and token counts when the provider reports them."""

    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None


class ProviderAdapter(Protocol):
    """One provider. ``call`` makes a single attempt or raises a ``ModelError``."""

    provider: str

    def call(self, request: ModelRequest, model: str, timeout: float) -> AdapterResult: ...


def chat_messages(request: ModelRequest) -> list[dict[str, Any]]:
    """The request's messages, with a JSON-only instruction first when a schema is set."""
    messages = list(request.messages)
    if request.response_schema is not None:
        schema = json.dumps(request.response_schema, sort_keys=True)
        instruction = (
            "Reply with exactly one JSON object and nothing else. "
            f"It must match this JSON schema: {schema}"
        )
        messages.insert(0, {"role": "system", "content": instruction})
    return messages


def _retry_after(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None  # an HTTP-date Retry-After falls back to the gateway's own backoff


def error_for_status(provider: str, status: int, retry_after: str | None = None) -> ModelError:
    """Map an HTTP error status to the typed error (BR3.2)."""
    if status in (401, 403):
        return ModelAuthError(provider, retryable=False, status=status)
    if status == 429:
        return ModelRateLimited(
            provider, retryable=True, status=status, retry_after=_retry_after(retry_after)
        )
    return ModelUnavailable(provider, retryable=status >= 500, status=status)


class OpenAICompatibleAdapter:
    """Chat completions over httpx for OpenAI-compatible APIs (Meta, hosted Llama)."""

    provider = "openai_compatible"

    def __init__(self, base_url: str, api_key: str, client: httpx.Client | None = None) -> None:
        self._url = f"{base_url.rstrip('/')}/chat/completions"
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self._client = client or httpx.Client()

    def call(self, request: ModelRequest, model: str, timeout: float) -> AdapterResult:
        """POST one chat completion and return its text and usage."""
        body = self._body(request, model)
        try:
            response = self._client.post(
                self._url, json=body, headers=self._headers, timeout=timeout
            )
        except httpx.TimeoutException:
            raise ModelTimeout(self.provider, retryable=True) from None
        except httpx.HTTPError:
            raise ModelUnavailable(self.provider, retryable=True, reason="connection") from None
        if response.status_code >= 400:
            raise error_for_status(
                self.provider, response.status_code, response.headers.get("retry-after")
            )
        return self._parse(response)

    def _body(self, request: ModelRequest, model: str) -> dict[str, Any]:
        return {
            "model": model,
            "messages": chat_messages(request),
            "max_tokens": request.max_tokens,
        }

    def _parse(self, response: httpx.Response) -> AdapterResult:
        try:
            data = response.json()
            text = data["choices"][0]["message"]["content"]
            usage = data.get("usage") or {}
            if not isinstance(text, str):
                raise TypeError("content is not text")
        except (ValueError, KeyError, IndexError, TypeError):
            raise ModelUnavailable(
                self.provider, retryable=True, reason="malformed provider reply"
            ) from None
        return AdapterResult(text, usage.get("prompt_tokens"), usage.get("completion_tokens"))


class MetaAdapter(OpenAICompatibleAdapter):
    """Meta Model API (OpenAI-compatible endpoint).

    Muse Spark models always reason, and reasoning tokens count against
    ``max_tokens``. Without headroom the reply is cut off before any answer
    text, so the reasoning effort is kept low and an allowance is added.
    """

    provider = "meta"
    REASONING_EFFORT = "low"
    REASONING_ALLOWANCE = 4000

    def _body(self, request: ModelRequest, model: str) -> dict[str, Any]:
        body = super()._body(request, model)
        body["max_tokens"] = request.max_tokens + self.REASONING_ALLOWANCE
        body["reasoning_effort"] = self.REASONING_EFFORT
        return body


class LlamaHostedAdapter(OpenAICompatibleAdapter):
    """A free hosted Llama tier (Groq by default, OpenRouter via the base URL)."""

    provider = "llama_hosted"


class ClaudeAdapter:
    """Claude through the anthropic SDK, with the SDK's own retries switched off."""

    provider = "claude"

    def __init__(
        self, api_key: str | None = None, base_url: str | None = None, client: Any = None
    ) -> None:
        if client is None:
            options: dict[str, Any] = {"api_key": api_key, "max_retries": 0}
            if base_url:
                options["base_url"] = base_url
            client = anthropic.Anthropic(**options)
        self._client = client

    def call(self, request: ModelRequest, model: str, timeout: float) -> AdapterResult:
        """Create one message and return its text and usage."""
        messages = chat_messages(request)
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        options: dict[str, Any] = {
            "model": model,
            "max_tokens": request.max_tokens,
            "messages": [m for m in messages if m["role"] != "system"],
            "timeout": timeout,
        }
        if system:
            options["system"] = system
        try:
            reply = self._client.messages.create(**options)
        except anthropic.APITimeoutError:
            raise ModelTimeout(self.provider, retryable=True) from None
        except anthropic.APIStatusError as exc:
            retry_after = exc.response.headers.get("retry-after")
            raise error_for_status(self.provider, exc.status_code, retry_after) from None
        except anthropic.APIConnectionError:
            raise ModelUnavailable(self.provider, retryable=True, reason="connection") from None
        text = "".join(
            block.text for block in reply.content if getattr(block, "type", None) == "text"
        )
        usage = getattr(reply, "usage", None)
        return AdapterResult(
            text,
            getattr(usage, "input_tokens", None),
            getattr(usage, "output_tokens", None),
        )


def request_hash(request: ModelRequest) -> str:
    """A stable short hash of what was asked, used to name recorded fixtures."""
    canonical = json.dumps(
        {
            "messages": request.messages,
            "maxTokens": request.max_tokens,
            "responseSchema": request.response_schema,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


class RecordedAdapter:
    """Replays saved replies: ``<dir>/<purpose>/<request hash>.json``, else ``default.json``.

    Needs no key and no network (NFR10.1). A fixture is ``{text, inputTokens, outputTokens}``.
    A fixture may instead hold ``replies``: a list of ``{match, text, ...}`` entries, and the
    first entry whose ``match`` text occurs in the request's messages is replayed (U4 uses
    this to record one reply per walk section). ``text`` at the top level, when present,
    is the reply when no entry matches.
    """

    provider = "recorded"

    def __init__(self, fixtures_dir: Path = DEFAULT_RECORDED_DIR) -> None:
        self._dir = fixtures_dir

    def call(self, request: ModelRequest, model: str, timeout: float) -> AdapterResult:
        """Return the recorded reply for this request, or raise ModelUnavailable."""
        folder = self._dir / request.purpose
        for path in (folder / f"{request_hash(request)}.json", folder / "default.json"):
            if path.is_file():
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    reply = _matching_reply(data, request)
                    if reply is None:
                        continue
                    return AdapterResult(
                        str(reply["text"]), reply.get("inputTokens"), reply.get("outputTokens")
                    )
                except (OSError, ValueError, KeyError, TypeError) as exc:
                    raise ModelUnavailable(
                        self.provider, retryable=False, reason=f"bad fixture {path.name}"
                    ) from exc
        raise ModelUnavailable(
            self.provider, retryable=False, reason=f"no recorded reply for {request.purpose}"
        )


def _matching_reply(data: dict[str, Any], request: ModelRequest) -> dict[str, Any] | None:
    """The fixture entry to replay: the first matching ``replies`` entry, else ``data``."""
    replies = data.get("replies")
    if replies is None:
        return data
    asked = "\n".join(str(m.get("content", "")) for m in request.messages)
    for reply in replies:
        if str(reply["match"]) in asked:
            matched: dict[str, Any] = reply
            return matched
    return data if "text" in data else None


def build_adapter(
    config: ProviderConfig,
    *,
    http_client: httpx.Client | None = None,
    recorded_dir: Path = DEFAULT_RECORDED_DIR,
) -> ProviderAdapter:
    """The adapter for the configured provider."""
    if config.provider == "recorded":
        return RecordedAdapter(recorded_dir)
    key = config.api_key.get_secret_value() if config.api_key else ""
    if config.provider == "claude":
        return ClaudeAdapter(api_key=key, base_url=config.base_url)
    base_url = config.base_url or ""
    if config.provider == "meta":
        return MetaAdapter(base_url, key, http_client)
    return LlamaHostedAdapter(base_url, key, http_client)
