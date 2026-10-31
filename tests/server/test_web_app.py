"""The built web app (U8) is served at ``/`` without shadowing ``/api`` (plan Step 11)."""

from __future__ import annotations

import dataclasses
import sqlite3
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from brahma.server.app import create_app
from brahma.server.config import ServerConfig
from tests.agent.conftest import make_gateway_for, recorded

INDEX = "<!doctype html><title>Brahma</title><div id='root'></div>"


def _gateway(conn: sqlite3.Connection) -> Any:
    return make_gateway_for(conn, recorded("demo"))


def _dist(tmp_path: Path) -> Path:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text(INDEX, encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log('brahma')", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("outside the dist folder", encoding="utf-8")
    return dist


def test_root_serves_index_and_api_still_works(config: ServerConfig, tmp_path: Path) -> None:
    built = dataclasses.replace(config, web_dist=_dist(tmp_path))
    app = create_app(built, gateway_factory=_gateway)
    with TestClient(app) as client:
        root = client.get("/")
        assert root.status_code == 200 and "id='root'" in root.text
        assert client.get("/assets/app.js").text == "console.log('brahma')"
        spa = client.get("/cases/BR-000001")  # an app route falls back to index.html
        assert spa.status_code == 200 and "id='root'" in spa.text
        health = client.get("/api/health")
        assert health.status_code == 200 and health.json()["status"] == "ok"
        missing = client.get("/api/no-such-route")
        assert missing.status_code == 404 and missing.json()["error"]["code"] == "http_404"
        escaped = client.get("/..%2Fsecret.txt")
        assert "outside the dist folder" not in escaped.text


def test_without_a_build_only_the_api_is_served(config: ServerConfig, tmp_path: Path) -> None:
    app = create_app(
        dataclasses.replace(config, web_dist=tmp_path / "missing"), gateway_factory=_gateway
    )
    with TestClient(app) as client:
        assert client.get("/").status_code == 404
        assert client.get("/api/health").status_code == 200


def test_recorded_dir_comes_from_the_environment(tmp_path: Path) -> None:
    config = ServerConfig.from_env(
        {"BRAHMA_MODEL_PROVIDER": "recorded", "BRAHMA_RECORDED_DIR": str(tmp_path)}
    )
    assert config.recorded_dir == tmp_path
    assert ServerConfig.from_env({"BRAHMA_MODEL_PROVIDER": "recorded"}).recorded_dir is None
    built = dataclasses.replace(config, db_path=tmp_path / "b.db", log_path=tmp_path / "b.log")
    app = create_app(built)
    with TestClient(app) as client:
        assert client.get("/api/health").json()["provider"]["provider"] == "recorded"
