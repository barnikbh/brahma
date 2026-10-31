"""Pydantic models for cases and treatment safety (entities.md, contract C5).

Python attributes are snake_case; the contract names are camelCase aliases (``caseId``,
``nodeIds``). Every model refuses unknown keys and is immutable once built. Patients are
synthetic only (NFR6.1); there is no import path for real records.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from brahma.knowledge.models import PackVersionRef

NOT_CHECKED_MESSAGE = "Not checked: no grounded safety data"
MAX_WEIGHT_KG = 400

Sex = Literal["female", "male", "unknown"]
Origin = Literal["clinic", "benchmark"]
CaseStatus = Literal["new", "needs_data", "answered", "out_of_knowledge", "follow_up_due"]
Author = Literal["doctor", "brahma", "system"]
MessageKind = Literal["text", "form", "form_answer", "pathway", "map_action"]
FormState = Literal["open", "submitted"]
ValidationState = Literal["ok", "invalid", "conflict", "confirm_range"]
SafetyCheck = Literal["allergy", "pregnancy", "interaction", "duplicate_class"]
SafetyStatus = Literal["ok", "conflict", "not_checked"]
LockState = Literal["held", "read_only"]


class CsModel(BaseModel):
    """Base model: camelCase aliases, snake_case attributes, unknown keys refused, immutable."""

    model_config = ConfigDict(
        extra="forbid",
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
        serialize_by_alias=True,
        frozen=True,
    )


# --- Patient and case ------------------------------------------------------------------


class NewPatient(CsModel):
    """A synthetic patient as entered on "Create new patient" (no ID yet)."""

    synthetic_name: str = Field(min_length=1, max_length=80)
    age: int = Field(ge=0, le=130)
    sex: Sex
    weight_kg: float | None = Field(default=None, gt=0, le=MAX_WEIGHT_KG)
    pregnancy_status: str | None = None
    comorbidities: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    current_medication: list[str] = Field(default_factory=list)


class Patient(NewPatient):
    """A stored synthetic patient. Exactly one per case."""

    patient_id: str


class PatientChange(CsModel):
    """The fields ``update_patient`` may change (BR1.4). Unknown keys are refused."""

    sex: Sex | None = None
    age: int | None = Field(default=None, ge=0, le=130)
    weight_kg: float | None = Field(default=None, gt=0, le=MAX_WEIGHT_KG)
    pregnancy_status: str | None = None
    comorbidities: list[str] | None = None
    allergies: list[str] | None = None
    current_medication: list[str] | None = None


class Case(CsModel):
    """A synthetic case: one patient, an owner, a pinned pack version and a status."""

    case_id: str
    patient_id: str
    owner_profile_id: str
    pinned_pack_version: PackVersionRef | None = None
    origin: Origin = "clinic"
    benchmark_run_id: str | None = None
    status: CaseStatus = "new"
    synthetic: Literal[True] = True
    created_at: str
    updated_at: str


class CaseSummary(CsModel):
    """One search result for the patient picker."""

    case_id: str
    patient_id: str
    synthetic_name: str
    status: CaseStatus
    updated_at: str


# --- Thread ----------------------------------------------------------------------------


class MessageIn(CsModel):
    """A message to append to a case thread."""

    author: Author
    kind: MessageKind
    body: dict[str, Any] = Field(default_factory=dict)
    form_kind: str | None = None

    @model_validator(mode="after")
    def _form_kind(self) -> MessageIn:
        if (self.kind == "form") != (self.form_kind is not None):
            raise ValueError("formKind is required for a form message and only for one")
        return self


class Message(CsModel):
    """A stored thread message. A form message moves from open to submitted only."""

    message_id: str
    case_id: str
    author: Author
    kind: MessageKind
    body: dict[str, Any]
    form_kind: str | None = None
    form_state: FormState | None = None
    created_at: str


# --- Findings --------------------------------------------------------------------------


class FindingIn(CsModel):
    """A finding as confirmed by the doctor, before validation."""

    kind: str = Field(min_length=1)
    name: str = Field(min_length=1)
    value: float | str | None = None
    unit: str | None = None
    duration: str | None = None


class Finding(CsModel):
    """A validated finding (BR2). ``entered_value`` keeps the original text."""

    finding_id: str
    case_id: str
    kind: str
    name: str
    value: float | str | None = None
    unit: str | None = None
    entered_value: str | None = None
    duration: str | None = None
    validation_state: ValidationState
    node_id: str | None = None


# --- Lock ------------------------------------------------------------------------------


class TabLock(CsModel):
    """The one tab allowed to edit a case."""

    case_id: str
    tab_id: str
    heartbeat_at: float


# --- Dose, safety and edits (value objects) --------------------------------------------


class DoseResult(CsModel):
    """A computed dose with its formula text, e.g. ``5 mg/kg × 58 kg = 290 mg``."""

    value: float
    unit: str
    formula: str
    node_ids: list[str] = Field(min_length=1)


class MissingWeight(CsModel):
    """A per-kg dose cannot be computed until the patient's weight is recorded."""

    node_id: str
    message: str = "Weight needed to compute a per-kg dose"


class SafetyResult(CsModel):
    """One safety check for one drug. ``ok`` or ``conflict`` always cite nodes (NFR8.2)."""

    check: SafetyCheck
    status: SafetyStatus
    node_ids: list[str] = Field(default_factory=list)
    message: str
    drug_node_id: str

    @model_validator(mode="after")
    def _grounded(self) -> SafetyResult:
        if self.status != "not_checked" and not self.node_ids:
            raise ValueError(f"a safety result of status {self.status} must cite a node")
        return self


class TreatmentEdit(CsModel):
    """A doctor's edit to a drug's values. Append-only; the latest per node is in effect."""

    edit_id: str
    case_id: str
    node_id: str
    original: dict[str, Any]
    new_values: dict[str, Any]
    editor_profile_id: str
    created_at: str


class EditOutcome(CsModel):
    """``apply_edit``'s result: the stored edit plus the re-run dose and safety checks."""

    edit: TreatmentEdit
    dose: DoseResult | MissingWeight
    safety: list[SafetyResult]
