"""Patients, cases, the tab lock, messages, patient edits, form drafts, treatment edits
and the map (C5, C8 R-02, FR12, FR4.8, FR4.9).

Routes that change a case need the tab lock (``require_lock``): without it they return
409 ``case_read_only`` (BR4.3).
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Header, Query, Response
from fastapi import Body as BodyParam

from brahma.agent.models import DISCLAIMER, MAX_TEXT_LENGTH, MapData, version_label
from brahma.cases.models import MessageIn, NewPatient, PatientChange
from brahma.knowledge.models import PackVersionRef
from brahma.server.deps import TAB_HEADER, ApiError, Body, LockDep, ProfileDep, ServicesDep
from brahma.server.mapview import session_map
from brahma.server.services import Services

router = APIRouter(tags=["core"])


class LockBody(Body):
    """``POST`` and ``DELETE /api/cases/{caseId}/lock``."""

    tab_id: str


class ChatMessage(Body):
    """``POST /api/cases/{caseId}/messages``: free text from the doctor."""

    text: str


class TreatmentEditBody(Body):
    """``POST /api/cases/{caseId}/treatment-edits``."""

    node_id: str
    new_values: dict[str, Any]


class TraverseBody(Body):
    """``POST /api/cases/{caseId}/traverse``: the chosen option node."""

    node_id: str


def case_view(shared: Services, case_id: str, tab_id: str | None = None) -> dict[str, Any]:
    """The C8 ``CaseView``, plus the latest walk's state for Retry (NFR8.4)."""
    case = shared.cases.get_case(case_id)
    lock = shared.cases.acquire_lock(case_id, tab_id) if tab_id else "read_only"
    newer = shared.cases.newer_version(case_id)
    walk = shared.engine.repo.latest_for_case(case_id)
    pinned: PackVersionRef | None = case.pinned_pack_version
    return {
        "case": case.model_dump(by_alias=True),
        "patient": shared.cases.get_patient(case_id).model_dump(by_alias=True),
        "messages": [m.model_dump(by_alias=True) for m in shared.cases.list_messages(case_id)],
        "formDrafts": shared.cases.get_form_drafts(case_id),
        "findings": [f.model_dump(by_alias=True) for f in shared.cases.list_findings(case_id)],
        "pinnedVersion": version_label(pinned),
        "newerVersion": version_label(newer),
        "lock": lock,
        "walk": None
        if walk is None
        else {
            "walkId": walk.walk_id,
            "status": walk.status,
            "waitingFor": walk.waiting_for,
            "lastSectionDone": walk.last_section_done,
            "counts": walk.counts.model_dump(),
            "packVersion": version_label(walk.pack_version),
            "canFollowUp": shared.engine.can_follow_up(walk),
        },
        "disclaimer": DISCLAIMER,
    }


@router.get("/patients")
def search_patients(
    shared: ServicesDep, profile: ProfileDep, q: Annotated[str, Query(max_length=200)] = ""
) -> dict[str, Any]:
    """The doctor's cases matching a case ID, finding or diagnosis (FR12.1, FR12.4)."""
    found = shared.cases.search_patients(q, profile)
    return {"results": [c.model_dump(by_alias=True) for c in found], "query": q}


@router.post("/patients", status_code=201)
def create_patient(patient: NewPatient, shared: ServicesDep, profile: ProfileDep) -> dict[str, Any]:
    """Create a synthetic patient and an empty case ``BR-xxxxxx`` (FR12.2)."""
    case = shared.cases.create_case(patient, profile)
    return case_view(shared, case.case_id)


@router.get("/cases/{case_id}")
def get_case(
    case_id: str,
    shared: ServicesDep,
    _profile: ProfileDep,
    tab_id: Annotated[str | None, Header(alias=TAB_HEADER)] = None,
) -> dict[str, Any]:
    """The case with its thread, drafts, pin and newer-version banner (FR12.3, FR1.7)."""
    return case_view(shared, case_id, tab_id)


@router.post("/cases/{case_id}/lock")
def acquire_lock(
    case_id: str, body: LockBody, shared: ServicesDep, _profile: ProfileDep
) -> dict[str, str]:
    """Take or heartbeat the one-tab lock."""
    return {"state": shared.cases.acquire_lock(case_id, body.tab_id)}


@router.delete("/cases/{case_id}/lock", status_code=204)
def release_lock(
    case_id: str,
    shared: ServicesDep,
    _profile: ProfileDep,
    body: Annotated[LockBody, BodyParam()],
) -> Response:
    """Release the lock when the tab closes."""
    shared.cases.release_lock(case_id, body.tab_id)
    return Response(status_code=204)


@router.post("/cases/{case_id}/messages", status_code=201)
def send_message(
    case_id: str, body: ChatMessage, shared: ServicesDep, _lock: LockDep
) -> dict[str, Any]:
    """Store free text; during a walk it is queued for "Review findings and re-walk" (BR2.9).

    After a walk has ended the web app sends chat text as a ``follow_up`` walk instead
    (``POST /walk``), so it is read as treatment history and answered at once."""
    text = body.text.strip()
    if not text or len(text) > MAX_TEXT_LENGTH:
        raise ApiError(422, "invalid_text", f"A message has 1 to {MAX_TEXT_LENGTH} characters.")
    message = MessageIn(author="doctor", kind="text", body={"text": text})
    message_id = shared.cases.append_message(case_id, message)
    return {"messageId": message_id, "offers": shared.engine.queue_message(case_id, message_id)}


@router.patch("/cases/{case_id}/patient")
def change_patient(
    case_id: str, body: PatientChange, shared: ServicesDep, profile: ProfileDep, lock: LockDep
) -> dict[str, Any]:
    """Change sex, weight, comorbidities or allergies; doses re-read at once (FR4.9)."""
    changes = body.model_dump(by_alias=True, exclude_unset=True)
    shared.cases.update_patient(case_id, changes, profile)
    return case_view(shared, case_id, lock)


@router.put("/cases/{case_id}/forms/{message_id}/draft", status_code=204)
def save_draft(
    case_id: str,
    message_id: str,
    values: Annotated[dict[str, Any], BodyParam()],
    shared: ServicesDep,
    _lock: LockDep,
) -> Response:
    """Keep unsubmitted form values (FR12.3)."""
    shared.cases.save_form_draft(case_id, message_id, values)
    return Response(status_code=204)


@router.post("/cases/{case_id}/treatment-edits", status_code=201)
def treatment_edit(
    case_id: str,
    body: TreatmentEditBody,
    shared: ServicesDep,
    profile: ProfileDep,
    _lock: LockDep,
) -> dict[str, Any]:
    """Apply a doctor's treatment edit; dose and safety are re-run (FR6)."""
    outcome = shared.cases.apply_edit(case_id, body.node_id, body.new_values, profile)
    return outcome.model_dump(by_alias=True)


@router.post("/cases/{case_id}/traverse", status_code=201)
def traverse(
    case_id: str,
    body: TraverseBody,
    shared: ServicesDep,
    profile: ProfileDep,
    _lock: LockDep,
) -> dict[str, Any]:
    """Record the doctor's chosen drug option and re-light its tier's path."""
    shared.cases.get_case(case_id)
    data, notice, path = shared.engine.traverse_choice(case_id, body.node_id, profile)
    return {
        "map": data.model_dump(by_alias=True),
        "notice": notice,
        "path": path.model_dump(by_alias=True),
    }


@router.get("/cases/{case_id}/map")
def case_map(
    case_id: str,
    shared: ServicesDep,
    _profile: ProfileDep,
    walk_id: Annotated[str | None, Query(alias="walkId")] = None,
    session_id: Annotated[str | None, Query(alias="sessionId")] = None,
) -> dict[str, Any]:
    """Map data for the latest walk, a given walk, or a replayed session (C8 R-02)."""
    shared.cases.get_case(case_id)
    data: MapData | None
    if session_id is not None:
        data = session_map(shared, session_id)
    else:
        data = shared.engine.map_data(case_id, walk_id)
    if data is None:
        empty = MapData(
            version=version_label(shared.cases.get_case(case_id).pinned_pack_version) or "",
            nodes=[],
            edges=[],
            selected_path=[],
        )
        return empty.model_dump(by_alias=True)
    return data.model_dump(by_alias=True)
