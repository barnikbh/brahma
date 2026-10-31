"""``POST /api/cases/{caseId}/walk``: the walk as Server-Sent Events (C8, BR4.3, BR4.4).

The route checks the session, the case and the tab lock before the stream opens (401,
404 and 409 are ordinary JSON errors). The stream's first event is ``progress``, sent
before any model call (NFR1). Failures during the stream arrive as an ``error`` event.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from brahma.agent.models import WalkRequest
from brahma.server.deps import LockDep, ProfileDep, ServicesDep

router = APIRouter(tags=["core"])

SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


@router.post("/cases/{case_id}/walk")
def walk(
    case_id: str, body: WalkRequest, shared: ServicesDep, profile: ProfileDep, _lock: LockDep
) -> StreamingResponse:
    """Start, continue, re-walk, explore or stop exploring; responds with an SSE stream."""
    shared.cases.get_case(case_id)

    async def events() -> AsyncIterator[str]:
        async for event in shared.engine.stream(case_id, body, profile):
            yield event.sse()

    return StreamingResponse(events(), media_type="text/event-stream", headers=SSE_HEADERS)
