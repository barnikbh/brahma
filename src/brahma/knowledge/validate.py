"""Validate pack files without a database.

Usage::

    python -m brahma.knowledge.validate content/ibd.yaml content/urology.yaml

Runs the same checks as ``load_pack`` (safe parsing, models, BR1.1, BR1.2, BR1.4, BR3.5
and the patient-data scan) and checks that pack codes are unique across the files.
Exits 0 when every file is valid, 1 otherwise.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence

from brahma.knowledge.errors import PackLoadError
from brahma.knowledge.loader import PackLoader
from brahma.knowledge.validator import PackValidator


def main(argv: Sequence[str] | None = None) -> int:
    """Validate each named pack file; print one line per file; return the exit code."""
    paths = list(sys.argv[1:] if argv is None else argv)
    if not paths:
        print("usage: python -m brahma.knowledge.validate PACK.yaml ...", file=sys.stderr)
        return 2
    loader, validator = PackLoader(), PackValidator()
    codes: dict[str, str] = {}
    failed = False
    for path in paths:
        try:
            pack = loader.read(path)
            validator.validate(pack.pack.code, pack.sources, pack.nodes, pack.edges)
            code = pack.pack.code
            if code in codes:
                raise PackLoadError(code, f"pack code also used by {codes[code]}")
            codes[code] = path
        except PackLoadError as exc:
            failed = True
            print(f"FAIL {path}: {exc}", file=sys.stderr)
            continue
        print(
            f"OK {path}: pack {pack.pack.code} v{pack.version}, {len(pack.nodes)} nodes, "
            f"{len(pack.edges)} edges, {len(pack.sources)} sources"
        )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
