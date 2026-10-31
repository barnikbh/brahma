"""Provider configuration, read from the environment at start (BR3.1, NFR5.1, NFR8.3)."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from typing import Literal, cast

from pydantic import Field, SecretStr

from brahma.platform.base import PfModel
from brahma.platform.errors import ConfigError

ProviderName = Literal["meta", "claude", "llama_hosted", "recorded"]

KEY_VARS: dict[str, str] = {
    "meta": "META_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
    "llama_hosted": "LLAMA_API_KEY",
}
# OpenAI-compatible defaults; override with BRAHMA_MODEL_BASE_URL (for example OpenRouter).
DEFAULT_BASE_URLS: dict[str, str] = {
    "meta": "https://api.llama.com/compat/v1",
    "llama_hosted": "https://api.groq.com/openai/v1",
}
RECORDED_MODEL = "recorded"


class ProviderConfig(PfModel):
    """The active model provider. The key is a ``SecretStr`` and never printed."""

    provider: ProviderName
    model: str = Field(min_length=1)
    api_key_env: str | None = None
    api_key: SecretStr | None = None
    base_url: str | None = None
    requests_per_minute: int = Field(default=30, ge=1, le=1000)
    timeout_seconds: int = Field(default=45, ge=5, le=120)

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> ProviderConfig:
        """Read ``BRAHMA_MODEL_*`` and the chosen provider's key variable.

        Empty values count as unset. Raises ConfigError naming the variable (never its
        value) when a required one is missing or invalid, or the base URL is not HTTPS.
        The ``recorded`` provider needs no key and no model name.
        """
        source = os.environ if env is None else env

        def get(name: str) -> str | None:
            value = source.get(name, "").strip()
            return value or None

        provider = get("BRAHMA_MODEL_PROVIDER")
        if provider is None:
            raise ConfigError("BRAHMA_MODEL_PROVIDER is not set")
        if provider not in (*KEY_VARS, "recorded"):
            raise ConfigError(
                "BRAHMA_MODEL_PROVIDER must be meta, claude, llama_hosted or recorded"
            )
        if provider == "recorded":
            return cls(provider="recorded", model=get("BRAHMA_MODEL_NAME") or RECORDED_MODEL)

        model = get("BRAHMA_MODEL_NAME")
        if model is None:
            raise ConfigError(f"BRAHMA_MODEL_NAME is not set (needed for provider {provider})")
        key_var = KEY_VARS[provider]
        key = get(key_var)
        if key is None:
            raise ConfigError(f"{key_var} is not set (needed for provider {provider})")
        base_url = get("BRAHMA_MODEL_BASE_URL") or DEFAULT_BASE_URLS.get(provider)
        if base_url is not None and not base_url.startswith("https://"):
            raise ConfigError("BRAHMA_MODEL_BASE_URL must start with https://")
        return cls(
            provider=cast(ProviderName, provider),
            model=model,
            api_key_env=key_var,
            api_key=SecretStr(key),
            base_url=base_url.rstrip("/") if base_url else None,
            requests_per_minute=_int_var(get, "BRAHMA_MODEL_RPM", 30, 1, 1000),
            timeout_seconds=_int_var(get, "BRAHMA_MODEL_TIMEOUT_S", 45, 5, 120),
        )


def _int_var(get: Callable[[str], str | None], name: str, default: int, low: int, high: int) -> int:
    raw = get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ConfigError(f"{name} must be a whole number from {low} to {high}") from None
    if not low <= value <= high:
        raise ConfigError(f"{name} must be a whole number from {low} to {high}")
    return value
