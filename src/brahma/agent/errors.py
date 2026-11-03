"""Typed errors raised by the grounded agent (functional-spec.md "Error Handling").

Every error carries a stable ``code`` (sent to the web app in an ``error`` event or the
C8 ``Error`` body), a plain message and whether a retry may help. Messages name IDs,
never clinical text or patient values.
"""

from __future__ import annotations


class AgentError(Exception):
    """Base class for every error U4 raises."""

    code = "agent_error"
    retryable = False

    def log_label(self) -> str:
        """The class name, which is the only error text written to logs."""
        return type(self).__name__


class WalkNotFound(AgentError):
    """No walk has this ID for this case."""

    code = "walk_not_found"

    def __init__(self, walk_id: str) -> None:
        super().__init__(f"unknown walk: {walk_id}")
        self.walk_id = walk_id


class WalkNotResumable(AgentError):
    """The walk cannot take this step, e.g. it has finished or waits for another form."""

    code = "walk_not_resumable"

    def __init__(self, walk_id: str, reason: str) -> None:
        super().__init__(f"walk {walk_id} cannot continue: {reason}")
        self.walk_id = walk_id
        self.reason = reason


class FindingsNotReady(AgentError):
    """A finding is invalid or in conflict, so the walk cannot start (C5 findings_ready)."""

    code = "findings_not_ready"

    def __init__(self, case_id: str) -> None:
        super().__init__(f"case {case_id} has invalid or conflicting findings; fix them first")
        self.case_id = case_id


class ExploreInvalid(AgentError):
    """An explore or stop_explore request names no alternative or no open lane."""

    code = "explore_invalid"

    def __init__(self, node_id: str, reason: str) -> None:
        super().__init__(f"cannot explore {node_id}: {reason}")
        self.node_id = node_id
        self.reason = reason


class TraverseInvalid(AgentError):
    """A traverse request names no option, no answered walk, or no offering tier."""

    code = "traverse_invalid"

    def __init__(self, node_id: str, reason: str) -> None:
        super().__init__(f"cannot traverse {node_id}: {reason}")
        self.node_id = node_id
        self.reason = reason


class WalkRequestInvalid(AgentError):
    """A walk request is missing a field its mode needs."""

    code = "invalid_request"

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class GuardFailed(AgentError):
    """The grounding guard raised an exception; the line counted as failed (NFR8.5)."""

    code = "guard_failure"
    retryable = True

    def __init__(self, error_class: str) -> None:
        super().__init__(f"the grounding check failed ({error_class}); no line was shown")
        self.error_class = error_class
