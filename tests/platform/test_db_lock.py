"""Overlapping threads on one shared platform connection queue instead of failing."""

from __future__ import annotations

import sqlite3
import threading

from brahma.platform.db import transaction

_THREADS = 8
_WRITES = 30


def test_shared_connection_survives_overlapping_transactions(conn: sqlite3.Connection) -> None:
    """Concurrent transactions and reads on the shared connection all succeed."""
    errors: list[BaseException] = []

    def worker(n: int) -> None:
        try:
            for i in range(_WRITES):
                with transaction(conn):
                    conn.execute(
                        "INSERT INTO pf_model_call_log (call_id, provider, model, purpose,"
                        " latency_ms, attempts, created_at) VALUES (?,?,?,?,?,?,?)",
                        (f"w{n}-{i}", "recorded", "recorded", "extract", 0, 1, "t"),
                    )
                conn.execute("SELECT COUNT(*) FROM pf_model_call_log").fetchone()
        except BaseException as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(_THREADS)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    if errors:
        raise errors[0]
    count = conn.execute("SELECT COUNT(*) FROM pf_model_call_log").fetchone()[0]
    assert count == _THREADS * _WRITES
