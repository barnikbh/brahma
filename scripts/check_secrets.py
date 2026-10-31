"""Scan tracked text files for strings that look like API keys (NFR5.1).

Run from the repository root::

    python scripts/check_secrets.py

Files come from ``git ls-files``; outside a git checkout the tree is walked, skipping
what `.gitignore` keeps out (``.venv``, ``data``, ``.env``, caches). Findings name the
file, line and pattern, never the matched text. Exit code 0 means nothing was found,
1 means at least one finding, 2 means the scan could not run.
"""

from __future__ import annotations

import re
import subprocess
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

PATTERNS: dict[str, re.Pattern[str]] = {
    "anthropic key (sk-ant-)": re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
    # Key bodies have no dash, so slugs such as sk-proj-management-dashboard do not match.
    "openai-style key (sk-)": re.compile(
        r"(?<![A-Za-z0-9])sk-(?!ant-)(?:proj-|svcacct-|admin-)?[A-Za-z0-9_]{20,}"
    ),
    "groq key (gsk_)": re.compile(r"gsk_[A-Za-z0-9]{20,}"),
    "long value after KEY=": re.compile(r"KEY=[\"']?[A-Za-z0-9+/_-]{32,}={0,2}"),
}
_SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "data",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}
_SKIP_FILES = {".env", ".coverage", ".DS_Store"}


def scan_text(text: str) -> list[tuple[int, str]]:
    """Return ``(line number, pattern name)`` for every suspicious line."""
    findings = []
    for number, line in enumerate(text.splitlines(), start=1):
        for name, pattern in PATTERNS.items():
            if pattern.search(line):
                findings.append((number, name))
    return findings


def _walk(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in _SKIP_DIRS or part.endswith(".egg-info") for part in relative.parts):
            continue
        if path.is_file() and path.name not in _SKIP_FILES:
            yield path


def tracked_files(root: Path) -> list[Path]:
    """Files git tracks under ``root``, or a filtered walk when git is unavailable."""
    try:
        listing = subprocess.run(
            ["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return list(_walk(root))
    return [root / name for name in listing.decode("utf-8").split("\0") if name]


def scan_files(paths: Iterable[Path], root: Path) -> list[str]:
    """Return one ``file:line: pattern`` finding per suspicious line in text files."""
    findings = []
    for path in paths:
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if b"\0" in data:
            continue  # binary
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        for number, name in scan_text(text):
            findings.append(f"{path.relative_to(root)}:{number}: looks like a {name}")
    return findings


def main(argv: Sequence[str] | None = None) -> int:
    """Print findings and return the exit code."""
    args = list(sys.argv[1:] if argv is None else argv)
    root = Path(args[0] if args else ".").resolve()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    findings = scan_files(tracked_files(root), root)
    for finding in findings:
        print(finding)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
