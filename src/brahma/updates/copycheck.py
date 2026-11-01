"""Possible verbatim copy detection and source passage selection (BR2.3, BR2.4; NFR8.3).

Text is normalised to lowercase words with punctuation stripped. A draft is flagged when
it contains any run of 26 consecutive source words, that is more than 25, found through
a set of the source's 26-word windows. The passage shown to the reviewer is the source
paragraph that shares the most distinct words with the change.
"""

from __future__ import annotations

import re

WINDOW = 26
MAX_PASSAGE_CHARS = 1200

_NON_WORD = re.compile(r"[^\w\s]+")


def normalise_words(text: str) -> list[str]:
    """Lowercase words with punctuation removed (``"Dose-dependent,"`` -> dose, dependent)."""
    return _NON_WORD.sub(" ", text.lower()).split()


def _windows(words: list[str]) -> set[tuple[str, ...]]:
    return {tuple(words[i : i + WINDOW]) for i in range(len(words) - WINDOW + 1)}


class CopyChecker:
    """Checks drafted text against one source's words."""

    def __init__(self, source_text: str) -> None:
        self._source_windows = _windows(normalise_words(source_text))

    def is_copy(self, draft_text: str) -> bool:
        """True when ``draft_text`` repeats more than 25 consecutive source words."""
        if not self._source_windows:
            return False
        words = normalise_words(draft_text)
        draft_windows = (tuple(words[i : i + WINDOW]) for i in range(len(words) - WINDOW + 1))
        return any(window in self._source_windows for window in draft_windows)


def split_passages(source_text: str) -> list[str]:
    """The source's non-empty lines (one per HTML block after fetching)."""
    return [line.strip() for line in source_text.splitlines() if line.strip()]


def best_passage(source_text: str, change_text: str) -> str | None:
    """The source passage sharing the most distinct words with the change, or None.

    Ties keep the earlier passage. Long passages are cut to 1,200 characters.
    """
    wanted = set(normalise_words(change_text))
    best: str | None = None
    best_score = 0
    for passage in split_passages(source_text):
        score = len(wanted & set(normalise_words(passage)))
        if score > best_score:
            best, best_score = passage, score
    if best is None:
        return None
    return best if len(best) <= MAX_PASSAGE_CHARS else best[: MAX_PASSAGE_CHARS - 1] + "…"


def best_excerpt(source_text: str, change_text: str, max_lines: int = 7) -> str | None:
    """The run of up to ``max_lines`` source lines that best matches the change, so a table
    split over short lines reads whole. A shared number counts for more than a shared word,
    since numbers are what a reviewer checks. Ties keep the earlier run."""
    wanted = set(normalise_words(change_text))
    lines = split_passages(source_text)
    best: list[str] = []
    best_score = 0
    for start in range(len(lines)):
        run = lines[start : start + max_lines]
        # Anchor the run on a line that matches, so it does not open on unrelated text.
        if not wanted & set(normalise_words(run[0])):
            continue
        shared = wanted & set(normalise_words(" ".join(run)))
        score = len(shared) + 2 * sum(word.isdigit() for word in shared)
        if score > best_score:
            best, best_score = run, score
    if not best:
        return None
    text = "\n".join(best)
    return text if len(text) <= MAX_PASSAGE_CHARS else text[: MAX_PASSAGE_CHARS - 1] + "…"
