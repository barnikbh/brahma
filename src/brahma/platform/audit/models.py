"""Audit models (entities.md AuditEntry and SessionRecord, contract C2 updated)."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field, model_validator

from brahma.platform.base import PfModel, check_payload_size

AuditKind = Literal[
    "case_created",
    "patient_updated",
    "session_recorded",
    "explore",
    "explored_not_acted",
    "line_held_back",
    "line_rejected",
    "treatment_edit",
    "traverse_choice",
    "treatment_history",
    "prescription_signed",
    "prescription_voided",
    "acknowledgement",
    "visit_recorded",
    "proposal_created",
    "proposal_published",
    "proposal_rejected",
    "disclaimer_accepted",
    "benchmark_run",
    "sign_in",
]
Outcome = Literal["answered", "needs_data", "out_of_knowledge", "error"]
NonEmptyStr = Annotated[str, Field(min_length=1)]


class AuditEntryIn(PfModel):
    """One audit event to append. ``profileId`` is required; payload is at most 256 KB."""

    kind: AuditKind
    case_id: str | None = None
    session_id: str | None = None
    profile_id: str = Field(min_length=1)
    pack_version: str | None = None
    provider: str | None = None
    model: str | None = None
    benchmark_run_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _payload_size(self) -> AuditEntryIn:
        check_payload_size(self.payload, "payload")
        return self


class AuditEntry(AuditEntryIn):
    """A stored audit entry."""

    entry_id: str
    created_at: str

    @classmethod
    def from_row(cls, row: Any, payload: dict[str, Any]) -> AuditEntry:
        """Build from a ``pf_audit_entry`` row and its decoded payload."""
        return cls(
            entry_id=row["entry_id"],
            kind=row["kind"],
            case_id=row["case_id"],
            session_id=row["session_id"],
            profile_id=row["profile_id"],
            pack_version=row["pack_version"],
            provider=row["provider"],
            model=row["model"],
            benchmark_run_id=row["benchmark_run_id"],
            payload=payload,
            created_at=row["created_at"],
        )


class SessionInputs(PfModel):
    """What the doctor typed, verbatim, plus the confirmed findings."""

    text: str
    findings: list[dict[str, Any]] = Field(default_factory=list)
    # A follow-up turn: the past therapies it used, as {drug, response, nodeIds}.
    history: list[dict[str, Any]] = Field(default_factory=list)


class SessionAnswer(PfModel):
    """The answer as shown: summary, sections with lines and node IDs, and counts."""

    summary: str
    sections: list[dict[str, Any]] = Field(default_factory=list)
    counts: dict[str, Any] = Field(default_factory=dict)


class SessionRecordIn(PfModel):
    """The snapshot of one walk (C2 updated: profileId, packVersion, provider, model)."""

    case_id: NonEmptyStr
    walk_id: NonEmptyStr
    profile_id: NonEmptyStr
    pack_version: NonEmptyStr
    provider: NonEmptyStr
    model: NonEmptyStr
    inputs: SessionInputs
    path_node_ids: list[str]
    answer: SessionAnswer
    sources: list[str]
    explanation: list[dict[str, Any]]
    outcome: Outcome
    benchmark_run_id: str | None = None

    @model_validator(mode="after")
    def _record_size(self) -> SessionRecordIn:
        check_payload_size(self.model_dump(mode="json"), "session record")
        return self


class SessionRecord(SessionRecordIn):
    """A stored session record."""

    session_id: str
    created_at: str


class SessionFilter(PfModel):
    """History filter (BR1.3). ``benchmarkRunId`` implies including benchmark sessions."""

    outcome: Outcome | None = None
    text: str | None = None
    include_benchmark: bool = False
    benchmark_run_id: str | None = None


class SessionSummary(PfModel):
    """One history row."""

    session_id: str
    case_id: str
    created_at: str
    label: str
    outcome: Outcome
    pack_version: str


class SessionDetail(PfModel):
    """A session record with its audit entries in time order (functional-spec W3)."""

    record: SessionRecord
    entries: list[AuditEntry]
