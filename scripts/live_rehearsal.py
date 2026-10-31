"""Start an isolated live server, run the scripted demo walk, shut it down.

Run from the repository root with the live provider configured::

    set -a && source .env && set +a && .venv/bin/python scripts/live_rehearsal.py

Uses the first free port in 8001-8003 with a fresh scratch database, so it never
touches a server already running on 8000 or the demo database in ``data/``. The
server log (metadata only, never keys or clinical text) goes to
``/tmp/live_server.log``. Exit code is the walk's (see ``live_walk.py``).
"""

from __future__ import annotations

import glob
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import IO

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))

import live_walk


def start_on_free_port() -> tuple[subprocess.Popen[bytes], str, IO[str]]:
    # Stays open for the server's whole life; closed by the caller.
    log = open("/tmp/live_server.log", "w", encoding="utf-8")  # noqa: SIM115
    for port in ("8001", "8002", "8003"):
        for stale in glob.glob("/tmp/live_rehearsal.db*"):
            os.remove(stale)
        base = f"http://127.0.0.1:{port}"
        server = subprocess.Popen(
            [".venv/bin/python", "-m", "brahma.server"],
            stdout=log,
            stderr=subprocess.STDOUT,
            env={
                **os.environ,
                "BRAHMA_PORT": port,
                "BRAHMA_DB_PATH": "/tmp/live_rehearsal.db",
                "BRAHMA_LOG_PATH": "/tmp/live_rehearsal_brahma.log",
            },
        )
        client = httpx.Client(base_url=base, timeout=5.0)
        for _ in range(30):
            try:
                if client.get("/api/health").status_code == 200:
                    live_walk.BASE = base
                    return server, base, log
            except httpx.ConnectError:
                pass
            if server.poll() is not None:
                break  # bind failed (or crashed): try the next port
            time.sleep(2)
        if server.poll() is None:
            server.terminate()
            server.wait(timeout=15)
    log.close()
    raise RuntimeError("no free port in 8001-8003; see /tmp/live_server.log")


def main() -> int:
    server, base, log = start_on_free_port()
    print(f"server healthy on {base}; starting live walk", flush=True)
    try:
        return live_walk.main()
    finally:
        server.terminate()
        try:
            server.wait(timeout=15)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=15)
        assert server.poll() is not None, "server survived SIGKILL?!"
        log.close()


if __name__ == "__main__":
    sys.exit(main())
