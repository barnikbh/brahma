"""The core C8 routers: auth, cases, walk, nodes and sessions."""

from brahma.server.routes import auth, cases, nodes, sessions, walk

ROUTERS = (auth.router, cases.router, walk.router, nodes.router, sessions.router)

__all__ = ["ROUTERS"]
