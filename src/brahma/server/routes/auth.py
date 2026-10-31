"""Profiles, sign-in, the disclaimer, mounted features and health (C3, C7, C8, FR15.1).

Signing in is picking a listed demo profile: there is no password and no other access
control is claimed (C3). Only ``/api/profiles``, ``POST /api/session`` and
``/api/health`` work without a session.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from brahma.agent.models import DISCLAIMER
from brahma.server.deps import Body, ProfileDep, ServicesDep
from brahma.server.services import Services

router = APIRouter(tags=["core"])

DISCLAIMER_VERSION = "1.0"
DISCLAIMER_TEXT = (
    f"{DISCLAIMER}. Brahma shows cited knowledge-graph content for synthetic cases only. "
    "It does not diagnose, it is not certified for clinical use, and the doctor decides."
)


class SignIn(Body):
    """``POST /api/session``."""

    profile_id: str


def pack_versions(shared: Services) -> str:
    """The live versions as ``"IBD 1.0; URO 0.1"``, packs sorted by code (C3)."""
    lives = sorted(shared.knowledge.repo.live_versions(), key=lambda v: v.pack)
    return "; ".join(f"{v.pack} {v.number}" for v in lives)


def _session_view(shared: Services, profile_id: str) -> dict[str, Any]:
    profile = shared.identity.get_profile(profile_id)
    packs = pack_versions(shared)
    return {
        "profile": profile.model_dump(by_alias=True),
        "packVersions": packs,
        "needsDisclaimer": bool(packs)
        and shared.identity.needs_disclaimer(profile_id, DISCLAIMER_VERSION, packs),
        "disclaimer": {"version": DISCLAIMER_VERSION, "text": DISCLAIMER_TEXT},
        "provider": shared.gateway.current().model_dump(by_alias=True),
    }


@router.get("/profiles")
def list_profiles(shared: ServicesDep) -> dict[str, Any]:
    """The demo profiles to sign in as (no session needed)."""
    return {"profiles": [p.model_dump(by_alias=True) for p in shared.identity.list_profiles()]}


@router.post("/session")
def sign_in(body: SignIn, request: Request, shared: ServicesDep) -> dict[str, Any]:
    """Sign in as a listed demo profile; 404 for an unknown one."""
    view = _session_view(shared, body.profile_id)
    request.session.clear()
    request.session["profileId"] = body.profile_id
    return view


@router.get("/session")
def current_session(shared: ServicesDep, profile: ProfileDep) -> dict[str, Any]:
    """Who is signed in, and whether the disclaimer must be accepted first."""
    return _session_view(shared, profile)


@router.delete("/session", status_code=204)
def sign_out(request: Request) -> None:
    """Sign out (clears the cookie)."""
    request.session.clear()


@router.post("/disclaimer")
def accept_disclaimer(shared: ServicesDep, profile: ProfileDep) -> dict[str, Any]:
    """Accept "Decision support, not diagnosis" for the live pack versions (FR15.1)."""
    packs = pack_versions(shared)
    acceptance_id = shared.identity.accept_disclaimer(profile, DISCLAIMER_VERSION, packs)
    return {"acceptanceId": acceptance_id, "packVersions": packs, "disclaimer": DISCLAIMER}


@router.get("/features")
def features(request: Request, _profile: ProfileDep) -> dict[str, Any]:
    """The mounted feature modules; the web app shows only their screens (C7)."""
    return {"features": list(request.app.state.features)}


@router.get("/health")
def health(shared: ServicesDep) -> dict[str, Any]:
    """Live pack versions, the model provider and the database status (NFR11.3)."""
    try:
        shared.conn.execute("SELECT 1").fetchone()
        database = "ok"
    except Exception:  # the health check reports, it never raises
        database = "error"
    lives = sorted(shared.knowledge.repo.live_versions(), key=lambda v: v.pack)
    return {
        "status": "ok" if database == "ok" else "degraded",
        "packs": [{"pack": v.pack, "number": v.number} for v in lives],
        "provider": shared.gateway.current().model_dump(by_alias=True),
        "database": database,
        "disclaimer": DISCLAIMER,
    }
