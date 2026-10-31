"""Flag long verbatim runs copied from guideline passages into a pack (BR3.6, C-R4).

Source passages are copyrighted and stay outside the repository. Keep one plain-text
file per source, named ``<sourceId>.txt`` (for example ``IBD-S2.txt``), in a folder of
your own, then run before committing pack changes::

    .venv/bin/python scripts/check_copy.py content/ibd.yaml --passages ~/brahma-passages

Every node's label and content is compared with the passages of the sources it cites.
Any run of more than 25 consecutive words that also appears in the passage is flagged.
Exit code 0 means nothing was flagged, 1 means at least one node must be rewritten,
2 means the command could not run.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Sequence
from pathlib import Path

from brahma.knowledge.errors import PackLoadError
from brahma.knowledge.loader import PackLoader

MAX_WORDS = 25
_WORD = re.compile(r"[a-z0-9]+(?:['’][a-z0-9]+)*")


def words(text: str) -> list[str]:
    """Lowercased words with punctuation removed."""
    return _WORD.findall(text.lower())


def find_copied_runs(text: str, passage: str, max_words: int = MAX_WORDS) -> list[str]:
    """Return each maximal run of more than ``max_words`` words of ``text`` found in ``passage``."""
    size = max_words + 1
    text_words, passage_words = words(text), words(passage)
    shingles = {tuple(passage_words[i : i + size]) for i in range(len(passage_words) - size + 1)}
    runs: list[tuple[int, int]] = []
    for start in range(len(text_words) - size + 1):
        if tuple(text_words[start : start + size]) in shingles:
            end = start + size
            if runs and start <= runs[-1][1]:
                runs[-1] = (runs[-1][0], end)
            else:
                runs.append((start, end))
    return [" ".join(text_words[a:b]) for a, b in runs]


def check_pack(pack_path: Path, passages: Path, max_words: int = MAX_WORDS) -> list[str]:
    """Return one finding line per copied run; missing passage files are skipped."""
    pack = PackLoader().read(pack_path)
    findings: list[str] = []
    for node in pack.nodes:
        for source_id in node.source_ids:
            passage_file = passages / f"{source_id}.txt"
            if not passage_file.is_file():
                continue
            passage = passage_file.read_text(encoding="utf-8")
            for run in find_copied_runs(f"{node.label}. {node.content}", passage, max_words):
                findings.append(f"{node.node_id} ({source_id}): {len(run.split())} words: {run}")
    return findings


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("packs", nargs="+", type=Path, help="pack YAML files to check")
    parser.add_argument("--passages", required=True, type=Path, help="folder of <sourceId>.txt")
    parser.add_argument("--max-words", type=int, default=MAX_WORDS)
    args = parser.parse_args(argv)
    if not args.passages.is_dir():
        print(f"passages folder not found: {args.passages}", file=sys.stderr)
        return 2
    flagged = False
    for pack_path in args.packs:
        try:
            findings = check_pack(pack_path, args.passages, args.max_words)
        except PackLoadError as exc:
            print(f"FAIL {pack_path}: {exc}", file=sys.stderr)
            return 2
        for finding in findings:
            flagged = True
            print(f"FLAG {pack_path}: {finding}")
        if not findings:
            print(f"OK {pack_path}: no run longer than {args.max_words} words copied")
    return 1 if flagged else 0


if __name__ == "__main__":
    raise SystemExit(main())
