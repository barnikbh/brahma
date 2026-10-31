"""``WalkLogger``: one JSON line per walk event to ``BRAHMA_LOG_PATH`` (NFR11.1, NFR11.2).

Only allow-listed fields are written: IDs, node IDs, counts, timings, the outcome, the
error class and the provider. Clinical text (the doctor's note, findings, model lines)
is never logged, whatever a caller passes in.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any

from brahma.platform.base import utc_now

DEFAULT_LOG_PATH = "./data/brahma.log"
LOG_PATH_VAR = "BRAHMA_LOG_PATH"
ALLOWED_FIELDS = frozenset(
    {
        "event",
        "walkId",
        "caseId",
        "laneId",
        "sectionId",
        "mode",
        "nodeIds",
        "pathNodeIds",
        "lines",
        "rejected",
        "counts",
        "outcome",
        "status",
        "packVersion",
        "provider",
        "model",
        "durationMs",
        "error",
        "code",
        "retryable",
    }
)

_fallback = logging.getLogger("brahma.agent")


def default_log_path() -> Path:
    """``BRAHMA_LOG_PATH`` when set and non-empty, else ``./data/brahma.log``."""
    return Path(os.environ.get(LOG_PATH_VAR) or DEFAULT_LOG_PATH)


class WalkLogger:
    """Appends allow-listed walk events as JSON lines; never raises into the walk."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else default_log_path()
        self._lock = threading.Lock()

    @staticmethod
    def clean(fields: dict[str, Any]) -> dict[str, Any]:
        """Keep only allow-listed fields (NFR11.2)."""
        return {k: v for k, v in fields.items() if k in ALLOWED_FIELDS}

    def log(self, event: str, **fields: Any) -> dict[str, Any]:
        """Write one line and return what was written."""
        entry = {"at": utc_now(), **self.clean({**fields, "event": event})}
        line = json.dumps(entry, ensure_ascii=False, sort_keys=True)
        try:
            with self._lock:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(line + "\n")
        except OSError as exc:
            # The walk must not fail because the log file cannot be written; say so.
            _fallback.error("walk log write failed: %s", type(exc).__name__)
        return entry
