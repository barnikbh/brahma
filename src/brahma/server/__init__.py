"""Brahma backend server (U4): the local FastAPI app behind the web app (C7, C8).

Decision support, not diagnosis. It runs locally only (``python -m brahma.server``,
bound to 127.0.0.1) and works on synthetic cases only.
"""

from brahma.server.app import create_app
from brahma.server.config import ENV_VARS, ServerConfig

__all__ = ["ENV_VARS", "ServerConfig", "create_app"]
