"""Node detail and node comments (C1, C5, C8 R-02, FR15.1).

Every node detail carries the pack version and the disclaimer (BR4.6). With a
``caseId``, a drug node also gets this patient's computed dose and safety checks.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Query

from brahma.agent.models import DISCLAIMER, version_label
from brahma.agent.views import dose_note
from brahma.knowledge.models import NodeComment, PackVersionRef
from brahma.server.deps import ApiError, Body, ProfileDep, ServicesDep
from brahma.server.mapview import parse_version

router = APIRouter(tags=["core"])


class CommentBody(Body):
    """``POST /api/nodes/{version}/{nodeId}/comments``."""

    text: str


def _version(text: str) -> PackVersionRef:
    version = parse_version(text)
    if version is None:
        raise ApiError(422, "invalid_version", "Name the version as IBD@1.0.")
    return version


def _updated(shared: ServicesDep, ref: PackVersionRef, node_id: str) -> dict[str, Any] | None:
    """Who last updated the node and when, or None for a node still as first loaded."""
    found = shared.updates().node_provenance(ref.pack, ref.number).get(node_id)
    return found.model_dump(mode="json", by_alias=True) if found else None


def _initial_version(shared: ServicesDep, ref: PackVersionRef) -> str:
    versions = shared.knowledge.list_versions(ref.pack)
    return versions[-1].number if versions else ref.number


@router.get("/nodes/{version}/{node_id}")
def node_detail(
    version: str,
    node_id: str,
    shared: ServicesDep,
    _profile: ProfileDep,
    case_id: Annotated[str | None, Query(alias="caseId")] = None,
) -> dict[str, Any]:
    """The node with its sources, comments and, for a case, dose and safety."""
    ref = _version(version)
    node = shared.knowledge.get_node(ref, node_id)
    sources = [s for s in shared.knowledge.sources(ref) if s.source_id in node.source_ids]
    detail: dict[str, Any] = {
        "node": node.model_dump(by_alias=True),
        "sources": [s.model_dump(by_alias=True) for s in sources],
        "comments": [c.model_dump(by_alias=True) for c in shared.knowledge.list_comments(node_id)],
        "safety": [],
        "dose": None,
        "edited": None,
        "updated": _updated(shared, ref, node_id),
        "initialVersion": _initial_version(shared, ref),
        "packVersion": version_label(ref),
        "disclaimer": DISCLAIMER,
    }
    if case_id is not None:
        edit = shared.cases.latest_edit(case_id, node_id)
        detail["edited"] = edit.model_dump(by_alias=True) if edit else None
        if node.type == "drug":
            dose = shared.cases.compute_dose(case_id, node_id)
            detail["dose"] = dose_note(dose)
            safety = shared.cases.safety_checks(case_id, [node_id])
            detail["safety"] = [s.model_dump(by_alias=True) for s in safety]
    return detail


@router.get("/nodes/{version}/{node_id}/comments")
def list_comments(
    version: str, node_id: str, shared: ServicesDep, _profile: ProfileDep
) -> dict[str, Any]:
    """Comments on a node, newest first."""
    shared.knowledge.get_node(_version(version), node_id)
    comments = shared.knowledge.list_comments(node_id)
    return {"comments": [c.model_dump(by_alias=True) for c in comments]}


@router.post("/nodes/{version}/{node_id}/comments", status_code=201)
def add_comment(
    version: str, node_id: str, body: CommentBody, shared: ServicesDep, profile: ProfileDep
) -> dict[str, Any]:
    """Add a comment as the signed-in doctor."""
    shared.knowledge.get_node(_version(version), node_id)
    comment_id = shared.knowledge.add_comment(node_id, profile, body.text)
    stored: NodeComment = next(
        c for c in shared.knowledge.list_comments(node_id) if c.comment_id == comment_id
    )
    return stored.model_dump(by_alias=True)
