"""``ServerConfig``: the backend server's settings, read from the environment (NFR5.1).

Secrets come only from the environment. ``BRAHMA_SESSION_SECRET`` signs the session
cookie; with the ``recorded`` model provider (tests, CI, local dry runs) a missing secret
is replaced by a random one per start, otherwise start-up fails naming the variable.
"""

from __future__ import annotations

import os
import secrets
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from brahma.agent.logging import DEFAULT_LOG_PATH, LOG_PATH_VAR
from brahma.platform.db import DEFAULT_DB_PATH
from brahma.platform.errors import ConfigError

DEFAULT_FEATURE_MODULES = ("brahma.updates.api",)
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
MIN_SECRET_LENGTH = 16
# Every variable the server reads beyond U2's (``.env.example`` lists each, empty).
ENV_VARS = (
    "BRAHMA_SESSION_SECRET",
    "BRAHMA_FEATURE_MODULES",
    LOG_PATH_VAR,
    "BRAHMA_HOST",
    "BRAHMA_PORT",
    "BRAHMA_RECORDED_DIR",
)
DEFAULT_WEB_DIST = Path("web/dist")


@dataclass(frozen=True)
class ServerConfig:
    """Where the server keeps its data and how it signs sessions. ``repr`` hides the secret."""

    session_secret: str = field(repr=False)
    feature_modules: tuple[str, ...] = DEFAULT_FEATURE_MODULES
    log_path: Path = Path(DEFAULT_LOG_PATH)
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    db_path: Path = Path(DEFAULT_DB_PATH)
    content_dir: Path = Path("content")
    # The built web app (U8), served at ``/`` when its ``index.html`` exists.
    web_dist: Path = DEFAULT_WEB_DIST
    # Fixture folder for the ``recorded`` provider; None keeps the gateway's default.
    recorded_dir: Path | None = None

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> ServerConfig:
        """Read the server variables. Raises ConfigError naming a missing or bad one."""
        source = os.environ if env is None else env

        def get(name: str) -> str | None:
            value = source.get(name, "").strip()
            return value or None

        secret = get("BRAHMA_SESSION_SECRET")
        if secret is None:
            if get("BRAHMA_MODEL_PROVIDER") != "recorded":
                raise ConfigError("BRAHMA_SESSION_SECRET is not set")
            secret = secrets.token_urlsafe(32)
        if len(secret) < MIN_SECRET_LENGTH:
            raise ConfigError(f"BRAHMA_SESSION_SECRET must be at least {MIN_SECRET_LENGTH} long")
        modules = get("BRAHMA_FEATURE_MODULES")
        features = (
            tuple(m.strip() for m in modules.split(",") if m.strip())
            if modules is not None
            else DEFAULT_FEATURE_MODULES
        )
        return cls(
            session_secret=secret,
            feature_modules=features,
            log_path=Path(get(LOG_PATH_VAR) or DEFAULT_LOG_PATH),
            host=get("BRAHMA_HOST") or DEFAULT_HOST,
            port=_port(get("BRAHMA_PORT")),
            db_path=Path(get("BRAHMA_DB_PATH") or DEFAULT_DB_PATH),
            recorded_dir=_optional_path(get("BRAHMA_RECORDED_DIR")),
        )


def _optional_path(raw: str | None) -> Path | None:
    return Path(raw) if raw is not None else None


def _port(raw: str | None) -> int:
    if raw is None:
        return DEFAULT_PORT
    try:
        port = int(raw)
    except ValueError:
        raise ConfigError("BRAHMA_PORT must be a whole number from 1 to 65535") from None
    if not 1 <= port <= 65535:
        raise ConfigError("BRAHMA_PORT must be a whole number from 1 to 65535")
    return port
