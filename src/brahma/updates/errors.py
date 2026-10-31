"""Typed errors raised by knowledge updates (functional-spec.md "Error Handling", NFR8.4).

Every error carries a ``log_label``: the only error text written to logs. Messages are
plain sentences safe to show a doctor; they never carry source page text or model output.
C1 validation errors (``PackLoadError``) and C3 ``Forbidden`` pass through unchanged.
"""

from __future__ import annotations


class UpdateError(Exception):
    """Base class for every error U5 raises."""

    def log_label(self) -> str:
        """The class name, which is the only error text written to logs."""
        return type(self).__name__


class ProposalNotFound(UpdateError):
    """No proposal has this ID."""

    def __init__(self, proposal_id: str) -> None:
        super().__init__(f"unknown proposal: {proposal_id}")
        self.proposal_id = proposal_id


class ProposalClosed(UpdateError):
    """The proposal was already published or rejected; both are terminal."""

    def __init__(self, proposal_id: str, status: str) -> None:
        super().__init__(f"proposal {proposal_id} is already {status}")
        self.proposal_id = proposal_id
        self.status = status


class ProposalInvalid(UpdateError):
    """A proposal cannot be built as asked, e.g. a change to a field that does not exist."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class CopyFlagged(UpdateError):
    """The proposal repeats more than 25 consecutive source words, so it cannot publish."""

    def __init__(self, proposal_id: str, node_ids: list[str]) -> None:
        super().__init__(
            f"proposal {proposal_id} may copy source text verbatim "
            f"({', '.join(node_ids)}); paraphrase it before publishing"
        )
        self.proposal_id = proposal_id
        self.node_ids = node_ids


class SourceFetchError(UpdateError):
    """A source URL could not be fetched (BR2.1, BR2.2).

    ``refused`` is true when the URL itself was refused by policy (scheme, private
    address, redirect target), which the API returns as 422; any other failure (timeout,
    size cap, HTTP error) is 502.
    """

    def __init__(self, reason: str, *, refused: bool = False) -> None:
        super().__init__(f"source could not be fetched: {reason}")
        self.reason = reason
        self.refused = refused

    def log_label(self) -> str:
        """The class name plus whether the URL was refused, never the URL itself."""
        return f"{type(self).__name__} {'refused' if self.refused else 'failed'}"


class DraftFailed(UpdateError):
    """Drafting from a source failed: the model call, its output, or validation (BR3.2)."""

    def __init__(self, reason: str, cause_label: str | None = None) -> None:
        super().__init__(f"the draft could not be made: {reason}")
        self.reason = reason
        self.cause_label = cause_label

    def log_label(self) -> str:
        """The class name plus the underlying error's label, when there is one."""
        name = type(self).__name__
        return f"{name} ({self.cause_label})" if self.cause_label else name


class ThreadNotFound(UpdateError):
    """No update conversation of the signed-in doctor has this ID."""

    def __init__(self, thread_id: str) -> None:
        super().__init__(f"unknown conversation: {thread_id}")
        self.thread_id = thread_id


class ThreadClosed(UpdateError):
    """The conversation stopped after too many unanswered rounds; start a new one."""

    def __init__(self, thread_id: str) -> None:
        super().__init__("this conversation has ended; start a new one with the details so far")
        self.thread_id = thread_id
