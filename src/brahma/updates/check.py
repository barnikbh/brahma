"""The background source checker (BR4.2): ``python -m brahma.updates.check``.

One run re-fetches every linked source and drafts a ``scheduled`` proposal for each one
that changed; nothing is published. A server can also run it on an interval with
``SourceCheckScheduler``; the interval is ``BRAHMA_SOURCE_CHECK_HOURS`` (default 24,
``0`` turns it off). The exit code is 0 when every source was checked, 1 when any failed
and 2 when the configuration is invalid.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
from collections.abc import Mapping, Sequence

from brahma.updates.models import SourceCheckRun
from brahma.updates.service import UpdateService

ENV_HOURS = "BRAHMA_SOURCE_CHECK_HOURS"
DEFAULT_HOURS = 24.0
MAX_HOURS = 24.0 * 31

logger = logging.getLogger("brahma.updates.check")


def check_interval_hours(env: Mapping[str, str] | None = None) -> float:
    """The interval in hours from ``BRAHMA_SOURCE_CHECK_HOURS``; 0 means off.

    Empty or unset means 24. Raises ValueError, naming the variable, for anything that
    is not a number from 0 to 744 (31 days).
    """
    source = os.environ if env is None else env
    raw = source.get(ENV_HOURS, "").strip()
    if not raw:
        return DEFAULT_HOURS
    try:
        hours = float(raw)
    except ValueError:
        raise ValueError(f"{ENV_HOURS} must be a number of hours from 0 to 744") from None
    if not 0 <= hours <= MAX_HOURS:
        raise ValueError(f"{ENV_HOURS} must be a number of hours from 0 to 744")
    return hours


class SourceCheckScheduler:
    """Runs ``check_sources`` every ``interval_s`` seconds on a daemon thread.

    A run that raises is logged by error class and the next run still happens.
    """

    def __init__(self, service: UpdateService, interval_s: float) -> None:
        if interval_s <= 0:
            raise ValueError("the interval must be positive; use 0 hours to not start one")
        self._service = service
        self._interval_s = interval_s
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.runs: list[SourceCheckRun] = []

    @classmethod
    def from_env(
        cls, service: UpdateService, env: Mapping[str, str] | None = None
    ) -> SourceCheckScheduler | None:
        """A scheduler for the configured interval, or None when it is 0 (off)."""
        hours = check_interval_hours(env)
        return cls(service, hours * 3600) if hours > 0 else None

    def start(self) -> None:
        """Start the background thread (the first run happens after one interval)."""
        if self._thread is None:
            self._thread = threading.Thread(target=self._loop, name="source-check", daemon=True)
            self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        """Ask the thread to stop and wait for it."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout)
            self._thread = None

    def _loop(self) -> None:
        while not self._stop.wait(self._interval_s):
            try:
                self.runs.append(self._service.check_sources())
            except Exception as exc:  # keep the scheduler alive; the error is logged
                crash = {"event": "source_check_crashed", "error": type(exc).__name__}
                logger.error(json.dumps(crash))


def main(argv: Sequence[str] | None = None) -> int:
    """Run one check and print its counts as JSON."""
    del argv  # no options
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        check_interval_hours()
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    service = UpdateService.open()
    try:
        run = service.check_sources()
    finally:
        service.close()
    print(json.dumps(run.model_dump(mode="json", by_alias=True), indent=2))
    return 1 if run.failed else 0


if __name__ == "__main__":
    sys.exit(main())
