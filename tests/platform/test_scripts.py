"""The `.env.example` check and the secret-pattern scan (NFR5.1, NFR5.2)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

from brahma.platform import ENV_VARS

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"


def _load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


env_check = _load("check_env_example")
secrets = _load("check_secrets")

# Built at run time so this file itself never matches the scanner's patterns.
FAKE_ANTHROPIC = "sk-" + "ant-" + "a1" * 15
FAKE_GROQ = "gsk" + "_" + "B2" * 15
FAKE_OPENAI = "sk-" + "proj-" + "C3" * 15


def test_repository_env_example_passes() -> None:
    assert env_check.main([str(SCRIPTS.parent / ".env.example")]) == 0


def test_env_example_missing_or_filled_variable_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    lines = [f"{name}=" for name in ENV_VARS if name != "LLAMA_API_KEY"]
    lines[0] = "BRAHMA_MODEL_PROVIDER=meta"
    path = tmp_path / ".env.example"
    path.write_text("# comment\n" + "\n".join(lines) + "\n", encoding="utf-8")

    assert env_check.main([str(path)]) == 1
    out = capsys.readouterr().out
    assert "missing: LLAMA_API_KEY" in out
    assert "has a value (must be empty): BRAHMA_MODEL_PROVIDER" in out
    assert "=meta" not in out
    assert env_check.main([str(tmp_path / "absent")]) == 2


def test_secret_scan_flags_key_patterns_without_printing_them(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "config.py").write_text(
        f'key = "{FAKE_ANTHROPIC}"\nother = "{FAKE_GROQ}"\nMETA_API_KEY={"Zm9v" * 10}\n'
        f'legacy = "{FAKE_OPENAI}"\n',
        encoding="utf-8",
    )
    (tmp_path / "image.bin").write_bytes(b"\0" + FAKE_ANTHROPIC.encode())
    (tmp_path / ".env").write_text(f"ANTHROPIC_API_KEY={FAKE_ANTHROPIC}\n", encoding="utf-8")

    assert secrets.main([str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "config.py:1: looks like a anthropic key (sk-ant-)" in out
    assert "config.py:2: looks like a groq key (gsk_)" in out
    assert "config.py:3: looks like a long value after KEY=" in out
    assert "config.py:4: looks like a openai-style key (sk-)" in out
    assert "image.bin" not in out and ".env:" not in out
    assert FAKE_ANTHROPIC not in out


def test_secret_scan_passes_clean_text(tmp_path: Path) -> None:
    (tmp_path / "notes.md").write_text(
        "Set META_API_KEY= in your .env; ask-for-help, risk-free and the slug\n"
        "sk-proj-management-dashboard are fine.\n",
        encoding="utf-8",
    )
    assert secrets.main([str(tmp_path)]) == 0
    assert secrets.main([str(tmp_path / "missing")]) == 2
