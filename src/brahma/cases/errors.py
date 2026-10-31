"""Typed errors raised by the cases library (functional-spec.md "Error Handling", NFR8.1).

Every error carries a ``log_label``: the only error text that is logged. Labels and
messages name IDs and the failing field, never patient values.
"""

from __future__ import annotations


class CaseError(Exception):
    """Base class for every error U3 raises."""

    def log_label(self) -> str:
        """The class name, which is the only error text written to logs."""
        return type(self).__name__


class CaseNotFound(CaseError):
    """No case has this ID."""

    def __init__(self, case_id: str) -> None:
        super().__init__(f"unknown case: {case_id}")
        self.case_id = case_id


class InvalidCase(CaseError):
    """A case cannot be created as asked, e.g. a benchmark case with no run ID (BR1.1)."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class MessageNotFound(CaseError):
    """No message with this ID belongs to the case."""

    def __init__(self, case_id: str, message_id: str) -> None:
        super().__init__(f"unknown message {message_id} in case {case_id}")
        self.case_id = case_id
        self.message_id = message_id


class InvalidPatientChange(CaseError):
    """A patient change names a field that cannot change, or a value out of range (BR1.4)."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class InvalidTreatmentEdit(CaseError):
    """A treatment edit does not fit the drug fields (BR4.4)."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class NotADrugNode(CaseError):
    """The node exists but is not a drug node, so it has no dose or safety checks."""

    def __init__(self, node_id: str) -> None:
        super().__init__(f"not a drug node: {node_id}")
        self.node_id = node_id


class FormAlreadySubmitted(CaseError):
    """A form message is no longer open; it moves from open to submitted once (BR1.5)."""

    def __init__(self, message_id: str) -> None:
        super().__init__(f"form already submitted or not a form: {message_id}")
        self.message_id = message_id
