"""Server configuration, the signed session cookie and the run command (NFR5.1, NFR7.2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from brahma.platform.errors import ConfigError
from brahma.server import __main__ as entry
from brahma.server.app import create_app
from brahma.server.config import DEFAULT_FEATURE_MODULES, ServerConfig
from brahma.server.session import SessionSigner

SECRET = "a-test-secret-that-is-long-enough"


def test_config_reads_the_environment() -> None:
    config = ServerConfig.from_env(
        {
            "BRAHMA_SESSION_SECRET": SECRET,
            "BRAHMA_FEATURE_MODULES": "brahma.updates.api, ",
            "BRAHMA_PORT": "8123",
            "BRAHMA_LOG_PATH": "logs/walk.log",
        }
    )
    assert config.feature_modules == ("brahma.updates.api",)
    assert (config.host, config.port, config.log_path) == ("127.0.0.1", 8123, Path("logs/walk.log"))
    assert SECRET not in repr(config)
    recorded = ServerConfig.from_env({"BRAHMA_MODEL_PROVIDER": "recorded"})
    assert len(recorded.session_secret) >= 16
    assert recorded.feature_modules == DEFAULT_FEATURE_MODULES


@pytest.mark.parametrize(
    ("env", "message"),
    [
        ({"BRAHMA_MODEL_PROVIDER": "meta"}, "BRAHMA_SESSION_SECRET is not set"),
        ({"BRAHMA_SESSION_SECRET": "short"}, "at least 16"),
        ({"BRAHMA_SESSION_SECRET": SECRET, "BRAHMA_PORT": "http"}, "BRAHMA_PORT"),
        ({"BRAHMA_SESSION_SECRET": SECRET, "BRAHMA_PORT": "70000"}, "BRAHMA_PORT"),
    ],
)
def test_config_errors_name_the_variable(env: dict[str, str], message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        ServerConfig.from_env(env)


def test_signed_sessions_expire_and_refuse_forgery() -> None:
    now = [1_000.0]
    signer = SessionSigner(SECRET, max_age=60, clock=lambda: now[0])
    value = signer.dumps({"profileId": "p-maya"})
    assert signer.loads(value) == {"profileId": "p-maya"}
    assert SessionSigner("another-secret-entirely").loads(value) == {}
    assert signer.loads("garbage") == {} and signer.loads(None) == {}
    assert signer.loads("bm90IGpzb24." + signer._sign("bm90IGpzb24")) == {}
    now[0] += 61
    assert signer.loads(value) == {}


def test_an_unknown_feature_module_fails_start_up(tmp_path: Path) -> None:
    config = ServerConfig(
        session_secret=SECRET,
        feature_modules=("brahma.no_such_feature",),
        db_path=tmp_path / "brahma.db",
        log_path=tmp_path / "brahma.log",
    )
    with pytest.raises(ConfigError, match="cannot load"):
        create_app(config)
    bad = ServerConfig(
        session_secret=SECRET,
        feature_modules=("brahma.agent",),
        db_path=tmp_path / "other.db",
        log_path=tmp_path / "brahma.log",
    )
    with pytest.raises(ConfigError, match="no router"):
        create_app(bad)


def test_the_run_command_starts_uvicorn_on_localhost(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("BRAHMA_DB_PATH", str(tmp_path / "brahma.db"))
    started: dict[str, object] = {}

    def fake_run(app: object, **kw: object) -> None:
        started.update(kw)
        app.state.services.close()  # type: ignore[attr-defined]

    monkeypatch.setattr(entry.uvicorn, "run", fake_run)
    assert entry.main() == 0
    assert (started["host"], started["port"], started["workers"]) == ("127.0.0.1", 8000, 1)
    monkeypatch.setenv("BRAHMA_MODEL_PROVIDER", "claude")
    assert entry.main() == 2
