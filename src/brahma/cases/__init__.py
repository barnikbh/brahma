"""Brahma cases and treatment safety (U3): synthetic patients, the chat thread, finding
validation, the one-tab lock, dose computation and safety checks.

Decision support, not diagnosis. Synthetic data only: there is no import of real
records. The public interface is contract C5: ``CaseService`` plus the models and typed
errors below. ``brahma.cases.safety`` holds pure dose and safety functions that U4's
grounding guard may call directly.
"""

from brahma.cases.db import cs_connect
from brahma.cases.errors import (
    CaseError,
    CaseNotFound,
    FormAlreadySubmitted,
    InvalidCase,
    InvalidPatientChange,
    InvalidTreatmentEdit,
    MessageNotFound,
    NotADrugNode,
)
from brahma.cases.models import (
    NOT_CHECKED_MESSAGE,
    Case,
    CaseSummary,
    DoseResult,
    EditOutcome,
    Finding,
    FindingIn,
    Message,
    MessageIn,
    MissingWeight,
    NewPatient,
    Patient,
    PatientChange,
    SafetyResult,
    TreatmentEdit,
)
from brahma.cases.service import CaseService, new_case_id

__all__ = [
    "NOT_CHECKED_MESSAGE",
    "Case",
    "CaseError",
    "CaseNotFound",
    "CaseService",
    "CaseSummary",
    "DoseResult",
    "EditOutcome",
    "Finding",
    "FindingIn",
    "FormAlreadySubmitted",
    "InvalidCase",
    "InvalidPatientChange",
    "InvalidTreatmentEdit",
    "Message",
    "MessageIn",
    "MessageNotFound",
    "MissingWeight",
    "NewPatient",
    "NotADrugNode",
    "Patient",
    "PatientChange",
    "SafetyResult",
    "TreatmentEdit",
    "cs_connect",
    "new_case_id",
]
