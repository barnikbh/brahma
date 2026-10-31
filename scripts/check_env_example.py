"""Check `.env.example` lists every variable U2 reads, each with an empty value (NFR5.2).

Run from the repository root::

    python scripts/check_env_example.py [path/to/.env.example]

Exit code 0 means the file is complete and empty, 1 means a variable is missing or has
a value, 2 means the file could not be read. A found value is never printed.
"""

from __future__ import annotations

import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

from brahma.platform import ENV_VARS


def check_env_example(text: str, required: Iterable[str] = ENV_VARS) -> list[str]:
    """Return one problem line per missing variable or non-empty value."""
    values: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, value = stripped.split("=", 1)
        values[name.strip().removeprefix("export ").strip()] = value.strip()
    problems = [f"missing: {name}" for name in required if name not in values]
    problems += [f"has a value (must be empty): {name}" for name, v in values.items() if v]
    return problems


def main(argv: Sequence[str] | None = None) -> int:
    """Print problems and return the exit code."""
    args = list(sys.argv[1:] if argv is None else argv)
    path = Path(args[0] if args else ".env.example")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"cannot read {path}: {exc.strerror}", file=sys.stderr)
        return 2
    problems = check_env_example(text)
    for problem in problems:
        print(f"{path}: {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
