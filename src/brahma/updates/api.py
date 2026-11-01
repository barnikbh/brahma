"""The C9 knowledge API: a FastAPI ``router`` and the C7 ``feature`` entry.

U4's server mounts ``router`` at ``/api/knowledge`` (C7) and overrides two dependencies
with its shared instances: ``get_update_service`` and ``current_profile``. The profile
comes from the ``X-Brahma-Profile`` header, which the server sets from the signed-in
session. Publish and reject check the reviewer role in the service (C3 ``require_role``).

Every typed error is mapped in one place (``error_response``, applied by the router's
route class) to a status code and a plain message, so the form can keep the doctor's
input (FR10.8): 404 unknown, 409 copy flag or closed, 403 not a reviewer, 422 refused URL
or invalid change, 502 fetch or draft failure.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import Field, ValidationError

from brahma.knowledge.errors import (
    BaseNotLive,
    NodeNotFound,
    PackBusy,
    PackLoadError,
    VersionNotFound,
)
from brahma.knowledge.models import PACK_CODE_PATTERN
from brahma.platform.errors import Forbidden, ProfileNotFound
from brahma.updates import browse
from brahma.updates.assistant import UpdateAssistant
from brahma.updates.errors import (
    CopyFlagged,
    DraftFailed,
    ProposalClosed,
    ProposalInvalid,
    ProposalNotFound,
    SourceFetchError,
    ThreadClosed,
    ThreadNotFound,
    UpdateError,
)
from brahma.updates.models import (
    MAX_COMMENT_LENGTH,
    MAX_MESSAGE_LENGTH,
    MAX_URL_LENGTH,
    Proposal,
    ProposalIn,
    ProposalStatus,
    Thread,
    UpModel,
)
from brahma.updates.service import UpdateService

feature: dict[str, Any] = {"name": "knowledge", "version": "1.0", "screens": ["knowledge"]}

logger = logging.getLogger("brahma.updates.api")

FORBIDDEN_MESSAGE = "Only a clinical reviewer can publish or reject proposals."
_STATUS_BY_ERROR: tuple[tuple[tuple[type[Exception], ...], int], ...] = (
    ((ProposalNotFound, ThreadNotFound, VersionNotFound, NodeNotFound, ProfileNotFound), 404),
    ((CopyFlagged, ProposalClosed, ThreadClosed, BaseNotLive), 409),
    ((Forbidden,), 403),
    ((ProposalInvalid, PackLoadError, ValidationError), 422),
    ((DraftFailed,), 502),
    ((PackBusy,), 503),
)


class NotSignedIn(Exception):
    """The request carried no session profile."""


def _status_for(exc: Exception) -> int | None:
    if isinstance(exc, NotSignedIn):
        return 401
    if isinstance(exc, SourceFetchError):
        return 422 if exc.refused else 502
    for types, status in _STATUS_BY_ERROR:
        if isinstance(exc, types):
            return status
    return None


def _message_for(exc: Exception) -> str:
    if isinstance(exc, Forbidden):
        return FORBIDDEN_MESSAGE
    if isinstance(exc, NotSignedIn):
        return "Sign in with a demo profile first."
    if isinstance(exc, ValidationError):
        names = sorted({str(e["loc"][0]) for e in exc.errors() if e["loc"]})
        return f"These fields are not valid: {', '.join(names) or 'request'}."
    return str(exc)


def error_response(exc: Exception) -> JSONResponse | None:
    """The JSON error for a known error, or None to let the server handle it."""
    status = _status_for(exc)
    if status is None:
        return None
    label = exc.log_label() if isinstance(exc, UpdateError) else type(exc).__name__
    logger.warning(json.dumps({"event": "knowledge_api_error", "status": status, "error": label}))
    body = {"error": {"code": type(exc).__name__, "message": _message_for(exc)}}
    return JSONResponse(status_code=status, content=body)


class ErrorMappingRoute(APIRoute):
    """A route that turns typed errors into plain JSON errors (the router's one handler)."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        handler = super().get_route_handler()

        async def mapped(request: Request) -> Response:
            try:
                return await handler(request)
            except Exception as exc:
                response = error_response(exc)
                if response is None:
                    raise
                return response

        return mapped


router = APIRouter(route_class=ErrorMappingRoute, tags=["knowledge"])

_service: UpdateService | None = None


def get_update_service() -> UpdateService:
    """The shared service; U4's server overrides this with its own instance."""
    global _service
    if _service is None:
        _service = UpdateService.open()
    return _service


def current_profile(
    x_brahma_profile: Annotated[str | None, Header(alias="X-Brahma-Profile")] = None,
) -> str:
    """The signed-in profile ID from the session header; 401 when it is missing."""
    if x_brahma_profile is None or not x_brahma_profile.strip():
        raise NotSignedIn
    return x_brahma_profile.strip()


Service = Annotated[UpdateService, Depends(get_update_service)]
ProfileId = Annotated[str, Depends(current_profile)]


class DraftRequest(UpModel):
    """Ask the model to draft node updates from a source page (W2)."""

    pack: str = Field(default="IBD", pattern=PACK_CODE_PATTERN)
    url: str = Field(min_length=1, max_length=MAX_URL_LENGTH)


class ReviewRequest(UpModel):
    """The reviewer's comment on a publish (optional) or a reject (required)."""

    comment: str | None = Field(default=None, max_length=MAX_COMMENT_LENGTH)


class UpdateMessage(UpModel):
    """A doctor's message in an update conversation: free text and source URLs."""

    text: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)
    thread_id: str | None = None
    pack: str = Field(default="IBD", pattern=PACK_CODE_PATTERN)


def _proposal_body(proposal: Proposal, service: UpdateService) -> dict[str, Any]:
    body = proposal.model_dump(mode="json", by_alias=True)
    body["copyFlaggedNodeIds"] = proposal.copy_flagged_node_ids
    body["proposerName"] = service.display_name(proposal.proposer_profile_id)
    body["reviewerName"] = service.display_name(proposal.reviewer_profile_id)
    urls = {c.source_url for c in proposal.changes if c.source_url}
    known = [*service.knowledge.repo.read_sources(proposal.pack), *proposal.change_set.add_sources]
    cited = {s.url: s for s in known if s.url in urls}
    body["citedSources"] = [s.model_dump(mode="json", by_alias=True) for s in cited.values()]
    return body


@router.get("/proposals")
def list_proposals(
    service: Service,
    _profile: ProfileId,
    pack: Annotated[str | None, Query(pattern=PACK_CODE_PATTERN)] = None,
    status: ProposalStatus | None = None,
) -> dict[str, Any]:
    """Proposals newest first, optionally one pack and one status."""
    return {"proposals": [_proposal_body(p, service) for p in service.list_proposals(pack, status)]}


@router.post("/proposals", status_code=201)
def create_proposal(body: ProposalIn, service: Service, profile: ProfileId) -> dict[str, Any]:
    """A doctor's proposal: node, change, comment, and optionally a source URL and section."""
    return _proposal_body(service.create_proposal(body, profile), service)


@router.post("/proposals/draft", status_code=201)
def draft_proposal(body: DraftRequest, service: Service, profile: ProfileId) -> dict[str, Any]:
    """Draft a proposal from a source page with the configured model."""
    return _proposal_body(service.draft_from_source(body.pack, body.url, profile), service)


@router.get("/proposals/{proposal_id}")
def get_proposal(proposal_id: str, service: Service, _profile: ProfileId) -> dict[str, Any]:
    """Before and after values, source passages and copy flags."""
    return _proposal_body(service.get_proposal(proposal_id), service)


@router.post("/proposals/{proposal_id}/publish")
def publish_proposal(
    proposal_id: str, body: ReviewRequest, service: Service, profile: ProfileId
) -> dict[str, Any]:
    """Reviewer only: publish as the pack's next live version."""
    return _proposal_body(service.publish(proposal_id, profile, body.comment), service)


@router.post("/proposals/{proposal_id}/reject")
def reject_proposal(
    proposal_id: str, body: ReviewRequest, service: Service, profile: ProfileId
) -> dict[str, Any]:
    """Reviewer only: reject with a comment."""
    return _proposal_body(service.reject(proposal_id, profile, body.comment or ""), service)


@router.get("/versions")
def list_versions(
    service: Service,
    _profile: ProfileId,
    pack: Annotated[str, Query(pattern=PACK_CODE_PATTERN)] = "IBD",
) -> dict[str, Any]:
    """Version history for one pack: live, superseded, proposed and rejected."""
    entries = service.version_history(pack)
    return {"pack": pack, "versions": [e.model_dump(mode="json", by_alias=True) for e in entries]}


# --- browse (read-only, no model) -------------------------------------------------------


@router.get("/packs")
def list_packs(service: Service, _profile: ProfileId) -> dict[str, Any]:
    """Each pack with its live version and all version numbers."""
    return {"packs": browse.list_packs(service)}


@router.get("/graph")
def pack_graph(
    service: Service,
    _profile: ProfileId,
    pack: Annotated[str, Query(pattern=PACK_CODE_PATTERN)] = "IBD",
    version: Annotated[str | None, Query(pattern=r"^\d+\.\d+$")] = None,
) -> dict[str, Any]:
    """Lightweight nodes and labelled edges of a pack version (live by default)."""
    return browse.pack_graph(service, pack, version)


@router.get("/nodes/{node_id}")
def node_view(
    node_id: str,
    service: Service,
    _profile: ProfileId,
    pack: Annotated[str, Query(pattern=PACK_CODE_PATTERN)] = "IBD",
    version: Annotated[str | None, Query(pattern=r"^\d+\.\d+$")] = None,
) -> dict[str, Any]:
    """One node: fields, sources, comments, connected nodes and who last updated it."""
    return browse.node_view(service, pack, version, node_id)


# --- update conversation ----------------------------------------------------------------


def _thread_body(thread: Thread, service: UpdateService) -> dict[str, Any]:
    body = thread.model_dump(mode="json", by_alias=True)
    body["profileName"] = service.display_name(thread.profile_id)
    proposals = {m.proposal_id for m in thread.messages if m.proposal_id}
    body["proposals"] = [
        _proposal_body(service.get_proposal(pid), service) for pid in sorted(proposals)
    ]
    return body


@router.post("/updates")
def send_update_message(
    body: UpdateMessage, service: Service, profile: ProfileId
) -> dict[str, Any]:
    """Start or continue an update conversation; the assistant drafts or asks."""
    thread = UpdateAssistant(service).send(profile, body.text, body.thread_id, body.pack)
    return _thread_body(thread, service)


@router.get("/updates")
def list_update_threads(service: Service, profile: ProfileId) -> dict[str, Any]:
    """The signed-in doctor's conversations, most recent first."""
    threads = UpdateAssistant(service).list_threads(profile)
    return {"threads": [_thread_body(t, service) for t in threads]}


@router.get("/updates/{thread_id}")
def get_update_thread(thread_id: str, service: Service, profile: ProfileId) -> dict[str, Any]:
    """One conversation with its messages and the proposals it produced."""
    return _thread_body(UpdateAssistant(service).get_thread(thread_id, profile), service)
