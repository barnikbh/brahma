"""``python -m brahma.server``: run the backend with uvicorn on 127.0.0.1:8000.

One process and one worker (NFR4.1). Host and port come from ``BRAHMA_HOST`` and
``BRAHMA_PORT``; everything else from the variables in ``.env.example``.
"""

from __future__ import annotations

import logging
import sys

import uvicorn

from brahma.platform.errors import ConfigError
from brahma.server.app import create_app
from brahma.server.config import ServerConfig


def main() -> int:
    """Start the server; print a plain message and exit 2 on a configuration error."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    try:
        config = ServerConfig.from_env()
        app = create_app(config)
    except ConfigError as exc:
        print(f"brahma.server: configuration error: {exc}", file=sys.stderr)
        return 2
    uvicorn.run(app, host=config.host, port=config.port, workers=1, log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
