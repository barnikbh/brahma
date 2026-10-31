"""Session history, audit detail with replay map, and export (C2, C8, FR9)."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query, Response

from brahma.agent.models import DISCLAIMER
from brahma.platform.audit.models import Outcome, SessionFilter
from brahma.server.deps import ProfileDep, ServicesDep
from brahma.server.mapview import session_map

router = APIRouter(tags=["core"])

MEDIA_TYPES = {"json": "application/json", "pdf": "application/pdf"}


@router.get("/sessions")
def list_sessions(
    shared: ServicesDep,
    _profile: ProfileDep,
    outcome: Outcome | None = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
    include_benchmark: Annotated[bool, Query(alias="includeBenchmark")] = False,
) -> dict[str, Any]:
    """History newest first; benchmark sessions only when asked for."""
    flt = SessionFilter(outcome=outcome, text=q, include_benchmark=include_benchmark)
    sessions = shared.audit.list_sessions(flt)
    return {"sessions": [s.model_dump(by_alias=True) for s in sessions]}


@router.get("/sessions/{session_id}")
def get_session(session_id: str, shared: ServicesDep, _profile: ProfileDep) -> dict[str, Any]:
    """The session record, its audit entries and the map to replay it."""
    detail = shared.audit.get_session(session_id)
    body: dict[str, Any] = detail.model_dump(mode="json", by_alias=True)
    body["map"] = session_map(shared, session_id).model_dump(by_alias=True)
    body["disclaimer"] = DISCLAIMER
    return body


@router.get("/sessions/{session_id}/export")
def export_session(
    session_id: str,
    shared: ServicesDep,
    _profile: ProfileDep,
    export_format: Annotated[Literal["json", "pdf"], Query(alias="format")] = "json",
) -> Response:
    """The full session as JSON or PDF."""
    data = shared.audit.export_session(session_id, export_format)
    filename = f"brahma-session-{session_id}.{export_format}"
    return Response(
        content=data,
        media_type=MEDIA_TYPES[export_format],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
