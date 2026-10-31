"""``create_app()``: the local FastAPI backend (C7, C8, BR4).

It builds the shared services once, adds the signed session cookie, mounts the core
routes under ``/api`` and each feature module listed in ``BRAHMA_FEATURE_MODULES`` under
``/api/<feature name>`` (C7). A mounted module's ``current_profile`` dependency is
overridden with the session's profile, so an ``X-Brahma-Profile`` header sent by a
client is never used (BR4.2). Every error body is the C8 ``Error``.
"""

from __future__ import annotations

import importlib
import json
import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from types import ModuleType
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from brahma.agent.errors import AgentError
from brahma.cases.errors import (
    CaseError,
    CaseNotFound,
    FormAlreadySubmitted,
    MessageNotFound,
)
from brahma.knowledge.errors import (
    CommentInvalid,
    KnowledgeError,
    NodeNotFound,
    VersionNotFound,
)
from brahma.platform.errors import (
    AuditInvalid,
    ConfigError,
    ExportFailed,
    Forbidden,
    PlatformError,
    ProfileNotFound,
    SessionNotFound,
)
from brahma.server.config import ServerConfig
from brahma.server.deps import ApiError, current_profile, error_body
from brahma.server.routes import ROUTERS
from brahma.server.services import GatewayFactory, Services
from brahma.server.session import SignedCookieSession

logger = logging.getLogger("brahma.server")

_STATUS: tuple[tuple[tuple[type[Exception], ...], int], ...] = (
    (
        (
            CaseNotFound,
            MessageNotFound,
            NodeNotFound,
            VersionNotFound,
            SessionNotFound,
            ProfileNotFound,
        ),
        404,
    ),
    ((FormAlreadySubmitted,), 409),
    ((Forbidden,), 403),
    ((ExportFailed,), 500),
    ((CaseError, CommentInvalid, AuditInvalid, AgentError, KnowledgeError), 422),
)


def _snake(name: str) -> str:
    return "".join(f"_{c.lower()}" if c.isupper() else c for c in name).lstrip("_")


def status_for(exc: Exception) -> int:
    """The HTTP status for a typed error (422 for any other known domain error)."""
    for types, status in _STATUS:
        if isinstance(exc, types):
            return status
    return 500


async def _domain_error(_request: Request, exc: Exception) -> JSONResponse:
    status = status_for(exc)
    code = exc.code if isinstance(exc, AgentError) else _snake(type(exc).__name__)
    message = str(exc) if status != 500 else "The server could not complete this request."
    logger.warning(
        json.dumps({"event": "api_error", "status": status, "error": type(exc).__name__})
    )
    return JSONResponse(status_code=status, content=error_body(code, message))


async def _api_error(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ApiError)
    return JSONResponse(status_code=exc.status, content=exc.body())


async def _http_error(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    return JSONResponse(
        status_code=exc.status_code, content=error_body(f"http_{exc.status_code}", str(exc.detail))
    )


async def _validation_error(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    names = sorted({str(e["loc"][-1]) for e in exc.errors() if e.get("loc")})
    message = f"These fields are not valid: {', '.join(names) or 'request'}."
    return JSONResponse(status_code=422, content=error_body("invalid_request", message))


def _mount_feature(app: FastAPI, name: str, services: Services) -> dict[str, Any]:
    """Mount one C7 module under ``/api/<feature name>`` and wire its dependencies."""
    try:
        module: ModuleType = importlib.import_module(name)
    except ImportError as exc:
        raise ConfigError(
            f"BRAHMA_FEATURE_MODULES names a module that cannot load: {name}"
        ) from exc
    router, feature = getattr(module, "router", None), getattr(module, "feature", None)
    if router is None or not isinstance(feature, dict) or "name" not in feature:
        raise ConfigError(f"feature module {name} has no router and feature entry (C7)")
    app.include_router(router, prefix=f"/api/{feature['name']}")
    overrides: dict[str, Callable[..., Any]] = {
        "current_profile": current_profile,
        "get_update_service": services.updates,
    }
    for attribute, replacement in overrides.items():
        dependency = getattr(module, attribute, None)
        if callable(dependency):
            app.dependency_overrides[dependency] = replacement
    return dict(feature)


def create_app(
    config: ServerConfig | None = None, *, gateway_factory: GatewayFactory | None = None
) -> FastAPI:
    """Build the app and its shared services (NFR4.1)."""
    settings = config or ServerConfig.from_env()
    services = Services.build(settings, gateway_factory)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield
        services.close()

    app = FastAPI(title="Brahma core API", version="1.0", lifespan=lifespan)
    app.state.services = services
    app.add_middleware(SignedCookieSession, secret=settings.session_secret)
    app.add_exception_handler(ApiError, _api_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    for error_type in (CaseError, KnowledgeError, PlatformError, AgentError):
        app.add_exception_handler(error_type, _domain_error)
    for router in ROUTERS:
        app.include_router(router, prefix="/api")
    try:
        app.state.features = [
            _mount_feature(app, name, services) for name in settings.feature_modules
        ]
    except ConfigError:
        services.close()
        raise
    mount_web_app(app, settings.web_dist)
    return app


def mount_web_app(app: FastAPI, dist: Path) -> bool:
    """Serve the built web app (U8) at ``/`` with an SPA fallback, when it is built.

    Files under ``dist`` are served as they are; any other GET path outside ``/api`` gets
    ``index.html`` so the app's own routes work on reload. ``/api`` is never shadowed: an
    unknown API path is still a C8 404. Returns whether the app was mounted.
    """
    root = dist.resolve()
    index = root / "index.html"
    if not index.is_file():
        logger.info("web app not built (%s missing); serving the API only", index)
        return False

    async def web_app(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise ApiError(404, "http_404", "Not Found")
        candidate = (root / path).resolve()
        if path and candidate.is_relative_to(root) and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index)

    app.add_api_route("/{path:path}", web_app, methods=["GET"], include_in_schema=False)
    return True
