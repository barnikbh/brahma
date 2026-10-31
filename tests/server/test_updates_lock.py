"""The lazy updates service builds exactly once under concurrent first use."""

from __future__ import annotations

import threading

from brahma.server.services import Services
from brahma.updates.service import UpdateService

_THREADS = 8


def test_updates_builds_once_under_threads(services: Services) -> None:
    """Concurrent first calls to updates() all get the same instance."""
    barrier = threading.Barrier(_THREADS)
    seen: list[UpdateService] = []
    seen_lock = threading.Lock()

    def worker() -> None:
        barrier.wait()
        built = services.updates()
        with seen_lock:
            seen.append(built)

    threads = [threading.Thread(target=worker) for _ in range(_THREADS)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(seen) == _THREADS
    assert all(built is seen[0] for built in seen)
