"""Overlapping threads on one shared knowledge connection queue instead of failing."""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Callable

from brahma.knowledge.repository import KnowledgeRepository

_THREADS = 8
_WRITES = 30


def test_shared_connection_survives_overlapping_transactions(
    connect: Callable[..., sqlite3.Connection],
) -> None:
    """Concurrent comment writes and reads on the shared connection all succeed."""
    repo = KnowledgeRepository(connect())
    errors: list[BaseException] = []

    def worker(n: int) -> None:
        try:
            for _ in range(_WRITES):
                with repo.transaction():
                    repo.insert_comment(f"node-{n}", "p-maya", "concurrent comment")
                repo.list_comments(f"node-{n}")
        except BaseException as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(_THREADS)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    if errors:
        raise errors[0]
    total = sum(len(repo.list_comments(f"node-{n}")) for n in range(_THREADS))
    assert total == _THREADS * _WRITES
