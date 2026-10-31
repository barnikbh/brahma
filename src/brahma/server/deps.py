"""Request dependencies and the C8 error shape (security-design.md NFR7.2, NFR8.1).

- ``services``: the shared ``Services`` of this app.
- ``current_profile``: the signed-in profile from the session cookie, else 401.
- ``require_lock``: the walk and edit routes need this tab to hold the case lock, else
  409 ``case_read_only`` (BR4.3). The tab names itself in the ``X-Brahma-Tab`` header.

Every HTTP error body is ``{"error": {code, message, retryable}}`` (the C8 ``Error``,
wrapped the same way U5's router wraps its errors).
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, Header, Request

from brahma.agent.models import AgModel
from brahma.platform.profiles import ProfileRepository
from brahma.server.services import Services

TAB_HEADER = "X-Brahma-Tab"


class ApiError(Exception):
    """An error with its HTTP status and C8 ``Error`` fields."""

    def __init__(self, status: int, code: str, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.retryable = retryable

    def body(self) -> dict[str, Any]:
        """The JSON body."""
        return error_body(self.code, self.message, self.retryable)


def error_body(code: str, message: str, retryable: bool = False) -> dict[str, Any]:
    """The C8 error body."""
    return {"error": {"code": code, "message": message, "retryable": retryable}}


class Body(AgModel):
    """Base request body: camelCase, unknown keys refused, immutable (NFR8.1)."""


def services(request: Request) -> Services:
    """The app's shared services."""
    shared: Services = request.app.state.services
    return shared


ServicesDep = Annotated[Services, Depends(services)]


def current_profile(request: Request, shared: ServicesDep) -> str:
    """The signed-in profile ID; 401 when no one is signed in (BR4.2)."""
    profile_id = request.session.get("profileId")
    if not isinstance(profile_id, str) or ProfileRepository(shared.conn).get(profile_id) is None:
        raise ApiError(401, "not_signed_in", "Sign in with a demo profile first.")
    return profile_id


ProfileDep = Annotated[str, Depends(current_profile)]


def require_lock(
    case_id: str,
    shared: ServicesDep,
    _profile: ProfileDep,
    tab_id: Annotated[str | None, Header(alias=TAB_HEADER)] = None,
) -> str:
    """The tab ID when this tab holds the case lock; 409 ``case_read_only`` otherwise."""
    if not tab_id or not tab_id.strip():
        raise ApiError(409, "case_read_only", "This tab has not taken the case; it is read-only.")
    if shared.cases.acquire_lock(case_id, tab_id.strip()) != "held":
        raise ApiError(
            409, "case_read_only", "The case is open in another tab; this one is read-only."
        )
    return tab_id.strip()


LockDep = Annotated[str, Depends(require_lock)]
