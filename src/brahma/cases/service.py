"""``CaseService``: the C5 facade over cases, findings, the tab lock, dose and safety.

It wires the ``cs_`` repository, the knowledge graph (C1) for nodes and units, and the
audit trail (C2). A patient update, a treatment edit and a new case write their audit
entry in the same ``BEGIN IMMEDIATE`` transaction as the ``cs_`` change, through U2's
``AuditRepository`` on the shared connection: if either write fails, both roll back
(NFR7.1). Logs carry the case ID, the operation and the error class, never patient values.
"""

from __future__ import annotations

import json
import logging
import secrets
import sqlite3
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, get_args

from pydantic import ValidationError

from brahma.cases.catalog import NodeCatalog
from brahma.cases.db import cs_connect
from brahma.cases.errors import (
    CaseError,
    CaseNotFound,
    FormAlreadySubmitted,
    InvalidCase,
    InvalidPatientChange,
    MessageNotFound,
)
from brahma.cases.findings import findings_ready as _findings_ready
from brahma.cases.findings import validate_findings
from brahma.cases.models import (
    Case,
    CaseStatus,
    CaseSummary,
    DoseResult,
    EditOutcome,
    Finding,
    FindingIn,
    LockState,
    Message,
    MessageIn,
    MissingWeight,
    NewPatient,
    Origin,
    Patient,
    PatientChange,
    SafetyResult,
    TreatmentEdit,
)
from brahma.cases.repository import CaseRepository
from brahma.cases.safety import (
    EffectiveDrug,
    edit_snapshot,
    effective_drug,
    resolve_edit,
)
from brahma.cases.safety import compute_dose as _compute_dose
from brahma.cases.safety import safety_checks as _safety_checks
from brahma.knowledge.errors import VersionNotFound
from brahma.knowledge.models import PackVersionRef, parse_version
from brahma.knowledge.repository import version_id
from brahma.knowledge.service import KnowledgeService
from brahma.platform.audit.models import AuditEntryIn, AuditKind
from brahma.platform.audit.repository import AuditRepository
from brahma.platform.base import new_id, utc_now
from brahma.platform.db import transaction
from brahma.platform.errors import AuditInvalid
from brahma.platform.profiles import ProfileRepository

logger = logging.getLogger("brahma.cases")

DEFAULT_PACK = "IBD"
CASE_ID_PREFIX = "BR-"
_CASE_ID_ATTEMPTS = 5
_LOCKED_PATIENT_FIELDS = ("sex", "age")


def new_case_id() -> str:
    """``BR-`` followed by 6 random hex characters (NFR6.1)."""
    return CASE_ID_PREFIX + secrets.token_hex(3).upper()


def _pack_label(version: PackVersionRef | None) -> str | None:
    return f"{version.pack} {version.number}" if version is not None else None


def _field_names(exc: ValidationError) -> str:
    names = sorted({str(err["loc"][0]) for err in exc.errors() if err["loc"]})
    return ", ".join(names) or "change"


class CaseService:
    """Synthetic cases and their treatment safety (contract C5)."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        knowledge: KnowledgeService,
        *,
        default_pack: str = DEFAULT_PACK,
        clock: Callable[[], float] = time.time,
    ) -> None:
        """``conn`` must hold the ``pf_`` and ``cs_`` tables (see ``cs_connect``)."""
        self._conn = conn
        self._repo = CaseRepository(conn)
        self._audit = AuditRepository(conn)
        self._profiles = ProfileRepository(conn)
        self._knowledge = knowledge
        self._default_pack = default_pack
        self._clock = clock
        self._catalogs: dict[str, NodeCatalog] = {}

    @classmethod
    def open(cls, path: str | Path | None = None) -> CaseService:
        """Open ``BRAHMA_DB_PATH`` (or ``path``) for cases, audit and knowledge."""
        conn = cs_connect(path)
        ProfileRepository(conn).seed()
        return cls(conn, KnowledgeService.open(path))

    def close(self) -> None:
        """Close the case connection and the knowledge service."""
        self._conn.close()
        self._knowledge.close()

    # --- cases and patients (BR1) ----------------------------------------------------

    def create_case(
        self,
        patient: NewPatient,
        owner_profile_id: str,
        origin: Origin = "clinic",
        benchmark_run_id: str | None = None,
    ) -> Case:
        """Store a synthetic patient and a new case ``BR-xxxxxx`` (BR1.1).

        Raises InvalidCase for a benchmark case with no run ID, AuditInvalid for an
        unknown owner profile.
        """
        if origin == "benchmark" and not benchmark_run_id:
            raise InvalidCase("a benchmark case needs a benchmarkRunId")
        if origin == "clinic" and benchmark_run_id is not None:
            raise InvalidCase("a clinic case has no benchmarkRunId")
        with self._logged("create_case", None):
            self._check_profile(owner_profile_id)
            now = utc_now()
            stored = Patient(patient_id=new_id("pt"), **patient.model_dump())
            case = Case(
                case_id=self._unused_case_id(),
                patient_id=stored.patient_id,
                owner_profile_id=owner_profile_id,
                origin=origin,
                benchmark_run_id=benchmark_run_id,
                created_at=now,
                updated_at=now,
            )
            with transaction(self._conn):
                self._repo.insert_patient(stored, now)
                self._repo.insert_case(case)
                self._add_audit(
                    "case_created",
                    case,
                    owner_profile_id,
                    {"origin": origin, "synthetic": True},
                )
            return case

    def search_patients(self, query: str, owner_profile_id: str) -> list[CaseSummary]:
        """The owner's clinic cases matching the case ID, a finding name or a diagnosis
        label in a pathway message, most recent first. A blank query lists the owner's
        recent cases (FR12.1)."""
        if not query.strip():
            return self._repo.recent(owner_profile_id)
        return self._repo.search(owner_profile_id, query)

    def get_case(self, case_id: str) -> Case:
        """The case; raises CaseNotFound."""
        case = self._repo.get_case(case_id)
        if case is None:
            raise CaseNotFound(case_id)
        return case

    def get_patient(self, case_id: str) -> Patient:
        """The case's patient; raises CaseNotFound."""
        patient = self._repo.get_patient(self.get_case(case_id).patient_id)
        if patient is None:
            raise CaseNotFound(case_id)
        return patient

    def update_patient(
        self, case_id: str, changes: dict[str, Any], editor_profile_id: str
    ) -> Patient:
        """Change allowed patient fields and write ``patient_updated`` in one transaction.

        Raises InvalidPatientChange for an unknown field or an out-of-range value (BR1.4).
        The caller re-reads ranges, doses and safety afterwards.
        """
        with self._logged("update_patient", case_id):
            case = self.get_case(case_id)
            patient = self.get_patient(case_id)
            updates = self._validated_change(changes)
            self._check_profile(editor_profile_id)
            updated = Patient.model_validate({**patient.model_dump(), **updates})
            before = patient.model_dump(by_alias=True)
            after = updated.model_dump(by_alias=True)
            changed = sorted(k for k in after if after[k] != before[k])
            with transaction(self._conn):
                self._repo.update_patient(updated, utc_now())
                self._repo.touch(case_id, utc_now())
                self._add_audit(
                    "patient_updated",
                    case,
                    editor_profile_id,
                    {
                        "fields": changed,
                        "before": {k: before[k] for k in changed},
                        "after": {k: after[k] for k in changed},
                    },
                )
            return updated

    def pin(self, case_id: str, version: PackVersionRef) -> None:
        """Pin the pack version a walk uses (BR1.3). Raises VersionNotFound."""
        self.get_case(case_id)
        if not any(v.number == version.number for v in self._knowledge.list_versions(version.pack)):
            raise VersionNotFound(version.pack, version.number)
        with transaction(self._conn):
            self._repo.set_pin(case_id, version, utc_now())

    def newer_version(self, case_id: str) -> PackVersionRef | None:
        """The live version when it is newer than the case's pin, else None (FR1.7)."""
        pinned = self.get_case(case_id).pinned_pack_version
        if pinned is None:
            return None
        live = self._knowledge.live_version(pinned.pack)
        return live if parse_version(live.number) > parse_version(pinned.number) else None

    def set_status(self, case_id: str, status: CaseStatus) -> None:
        """Set the case status (U4 calls this after a walk)."""
        self.get_case(case_id)
        if status not in get_args(CaseStatus):
            raise InvalidCase(f"unknown status: {status}")
        with transaction(self._conn):
            self._repo.set_status(case_id, status, utc_now())

    # --- thread and forms (BR1.5) ----------------------------------------------------

    def append_message(self, case_id: str, message: MessageIn) -> str:
        """Append a message to the thread and return its ID. A form message starts open."""
        self.get_case(case_id)
        now = utc_now()
        stored = Message(
            message_id=new_id("msg"),
            case_id=case_id,
            author=message.author,
            kind=message.kind,
            body=message.body,
            form_kind=message.form_kind,
            form_state="open" if message.kind == "form" else None,
            created_at=now,
        )
        with transaction(self._conn):
            self._repo.insert_message(stored)
            self._repo.touch(case_id, now)
        return stored.message_id

    def list_messages(self, case_id: str) -> list[Message]:
        """The thread in the order it was written."""
        self.get_case(case_id)
        return self._repo.list_messages(case_id)

    def save_form_draft(self, case_id: str, message_id: str, values: dict[str, Any]) -> None:
        """Keep unsubmitted values for an open form (FR12.3).

        Raises MessageNotFound, or FormAlreadySubmitted when the form is not open.
        """
        self._open_form(case_id, message_id)
        with transaction(self._conn):
            self._repo.save_draft(case_id, message_id, values, utc_now())

    def get_form_drafts(self, case_id: str) -> dict[str, dict[str, Any]]:
        """Unsubmitted form values by message ID."""
        self.get_case(case_id)
        return self._repo.get_drafts(case_id)

    def submit_form(self, case_id: str, message_id: str) -> None:
        """Move an open form to submitted, once, and delete its draft (BR1.5)."""
        self._open_form(case_id, message_id)
        with transaction(self._conn):
            if not self._repo.submit_form(message_id):
                raise FormAlreadySubmitted(message_id)
            self._repo.delete_draft(message_id)
            self._repo.touch(case_id, utc_now())

    # --- findings (BR2) --------------------------------------------------------------

    def set_findings(self, case_id: str, findings: list[FindingIn]) -> list[Finding]:
        """Validate the findings against the version in effect and replace the set."""
        case = self.get_case(case_id)
        catalog = self._catalog(self._version(case))
        validated = validate_findings(case_id, findings, catalog, lambda: new_id("f"))
        with transaction(self._conn):
            self._repo.replace_findings(case_id, validated)
            self._repo.touch(case_id, utc_now())
        return validated

    def list_findings(self, case_id: str) -> list[Finding]:
        """The case's findings in the order they were set."""
        self.get_case(case_id)
        return self._repo.list_findings(case_id)

    def findings_ready(self, case_id: str) -> bool:
        """True when no finding is invalid or in conflict, so a walk may start (BR2.7)."""
        return _findings_ready(self.list_findings(case_id))

    # --- tab lock (BR3) --------------------------------------------------------------

    def acquire_lock(self, case_id: str, tab_id: str) -> LockState:
        """``held`` when free, ours (heartbeat refreshed) or older than 45 s; else
        ``read_only``."""
        self.get_case(case_id)
        return self._repo.acquire_lock(case_id, tab_id, self._clock())

    def release_lock(self, case_id: str, tab_id: str) -> None:
        """Release the lock if ``tab_id`` holds it; otherwise do nothing."""
        self.get_case(case_id)
        self._repo.release_lock(case_id, tab_id)

    # --- dose, safety and edits (BR4) ------------------------------------------------

    def compute_dose(self, case_id: str, node_id: str) -> DoseResult | MissingWeight:
        """The dose for a drug node after any edit; MissingWeight when a per-kg dose has
        no weight (BR4.1). Raises NodeNotFound or NotADrugNode."""
        case = self.get_case(case_id)
        drug = self._effective(case, node_id)
        return _compute_dose(drug, self.get_patient(case_id).weight_kg)

    def safety_checks(self, case_id: str, drug_node_ids: list[str]) -> list[SafetyResult]:
        """Allergy, pregnancy, interaction and duplicate-class checks for each drug, never
        ``ok`` without a node (BR4.2, BR4.3)."""
        case = self.get_case(case_id)
        drugs = [self._effective(case, node_id) for node_id in drug_node_ids]
        catalog = self._catalog(self._version(case))
        return _safety_checks(drugs, self.get_patient(case_id), catalog)

    def apply_edit(
        self, case_id: str, node_id: str, new_values: dict[str, Any], editor_profile_id: str
    ) -> EditOutcome:
        """Store a treatment edit with its original values, write ``treatment_edit`` to the
        audit in the same transaction, and return it with the re-run dose and safety
        (BR4.4). A drug change resets route, dose and frequency to the new drug's values."""
        with self._logged("apply_edit", case_id):
            case = self.get_case(case_id)
            current = self._effective(case, node_id)
            catalog = self._catalog(self._version(case))
            snapshot = resolve_edit(current, new_values, catalog)
            self._check_profile(editor_profile_id)
            edit = TreatmentEdit(
                edit_id=new_id("te"),
                case_id=case_id,
                node_id=node_id,
                original=edit_snapshot(current),
                new_values=snapshot,
                editor_profile_id=editor_profile_id,
                created_at=utc_now(),
            )
            with transaction(self._conn):
                self._repo.insert_edit(edit)
                self._repo.touch(case_id, edit.created_at)
                payload = {
                    "editId": edit.edit_id,
                    "nodeId": node_id,
                    "original": edit.original,
                    "newValues": edit.new_values,
                }
                self._add_audit("treatment_edit", case, editor_profile_id, payload)
            return EditOutcome(
                edit=edit,
                dose=self.compute_dose(case_id, node_id),
                safety=self.safety_checks(case_id, [node_id]),
            )

    # --- internals -------------------------------------------------------------------

    def _version(self, case: Case) -> PackVersionRef:
        """The pinned version, or the default pack's live version before any walk."""
        if case.pinned_pack_version is not None:
            return case.pinned_pack_version
        return self._knowledge.live_version(self._default_pack)

    def _catalog(self, version: PackVersionRef) -> NodeCatalog:
        key = version_id(version.pack, version.number)
        catalog = self._catalogs.get(key)
        if catalog is None:
            nodes = self._knowledge.repo.read_nodes(key)
            if not nodes:
                raise VersionNotFound(version.pack, version.number)
            catalog = NodeCatalog(nodes)
            self._catalogs[key] = catalog
        return catalog

    def _effective(self, case: Case, node_id: str) -> EffectiveDrug:
        catalog = self._catalog(self._version(case))
        edit = self._repo.latest_edit(case.case_id, node_id)
        return effective_drug(catalog.get(node_id), edit.new_values if edit else None, catalog)

    def _open_form(self, case_id: str, message_id: str) -> Message:
        self.get_case(case_id)
        message = self._repo.get_message(case_id, message_id)
        if message is None:
            raise MessageNotFound(case_id, message_id)
        if message.form_state != "open":
            raise FormAlreadySubmitted(message_id)
        return message

    @staticmethod
    def _validated_change(changes: dict[str, Any]) -> dict[str, Any]:
        try:
            change = PatientChange.model_validate(changes)
        except ValidationError as exc:
            raise InvalidPatientChange(f"invalid or unknown fields: {_field_names(exc)}") from None
        updates = change.model_dump(exclude_unset=True)
        if not updates:
            raise InvalidPatientChange("no fields to change")
        cleared = [k for k in _LOCKED_PATIENT_FIELDS if k in updates and updates[k] is None]
        if cleared:
            raise InvalidPatientChange(f"fields that cannot be cleared: {', '.join(cleared)}")
        return updates

    def _unused_case_id(self) -> str:
        for _ in range(_CASE_ID_ATTEMPTS):
            case_id = new_case_id()
            if not self._repo.case_exists(case_id):
                return case_id
        raise InvalidCase("could not generate an unused case ID")

    def _check_profile(self, profile_id: str) -> None:
        if self._profiles.get(profile_id) is None:
            raise AuditInvalid(f"unknown profile: {profile_id}")

    def _add_audit(
        self, kind: AuditKind, case: Case, profile_id: str, payload: dict[str, Any]
    ) -> str:
        """Write one C2 audit entry inside the caller's open transaction."""
        return self._audit.add_entry(
            AuditEntryIn(
                kind=kind,
                case_id=case.case_id,
                profile_id=profile_id,
                pack_version=_pack_label(case.pinned_pack_version),
                benchmark_run_id=case.benchmark_run_id,
                payload=payload,
            )
        )

    @contextmanager
    def _logged(self, operation: str, case_id: str | None) -> Iterator[None]:
        """Log one structured line when an operation fails, then re-raise the error."""
        try:
            yield
        except (CaseError, sqlite3.Error, AuditInvalid, VersionNotFound) as exc:
            label = exc.log_label() if isinstance(exc, CaseError) else type(exc).__name__
            entry = {"event": operation, "caseId": case_id, "result": "error", "error": label}
            logger.warning(json.dumps(entry, sort_keys=True))
            raise
