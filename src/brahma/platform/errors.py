"""Typed errors raised by the platform (functional-spec.md "Error Handling", contract C4).

No error message ever carries a key, a provider response body or prompt text (NFR5.1).
"""

from __future__ import annotations


class PlatformError(Exception):
    """Base class for every error U2 raises."""


# --- Audit (C2) --------------------------------------------------------------------------


class AuditImmutable(PlatformError):
    """An UPDATE or DELETE reached an append-only table; nothing changed (BR1.1)."""


class AuditInvalid(PlatformError):
    """An entry or session record was refused: unknown profile, missing field or oversize."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class SessionNotFound(PlatformError):
    """No session record has this ID."""

    def __init__(self, session_id: str) -> None:
        super().__init__(f"unknown session: {session_id}")
        self.session_id = session_id


class ExportFailed(PlatformError):
    """The export could not be produced; nothing partial is returned (BR1.4)."""


# --- Identity (C3) -----------------------------------------------------------------------


class ProfileNotFound(PlatformError):
    """The profile ID is unknown (or not listed, for sign-in)."""

    def __init__(self, profile_id: str) -> None:
        super().__init__(f"unknown profile: {profile_id}")
        self.profile_id = profile_id


class Forbidden(PlatformError):
    """The profile's role does not allow this action (BR2.3)."""

    def __init__(self, profile_id: str, required_role: str) -> None:
        super().__init__(f"profile {profile_id} lacks role {required_role}")
        self.profile_id = profile_id
        self.required_role = required_role


# --- Model gateway (C4) ------------------------------------------------------------------


class ConfigError(PlatformError):
    """Provider configuration is missing or invalid. Names variables, never their values."""


class ModelError(PlatformError):
    """A model call failed. Carries the provider, whether a retry may help and the status."""

    def __init__(
        self,
        provider: str,
        *,
        retryable: bool,
        status: int | None = None,
        reason: str | None = None,
        retry_after: float | None = None,
    ) -> None:
        detail = reason or type(self).__name__
        suffix = f" (HTTP {status})" if status is not None else ""
        super().__init__(f"{provider}: {detail}{suffix}")
        self.provider = provider
        self.retryable = retryable
        self.status = status
        self.reason = reason
        self.retry_after = retry_after

    def log_label(self) -> str:
        """The only error text logged or stored: the class name plus the HTTP status."""
        name = type(self).__name__
        return f"{name} {self.status}" if self.status is not None else name


class ModelTimeout(ModelError):
    """The provider did not answer within the timeout."""


class ModelRateLimited(ModelError):
    """The provider returned 429, or asked for a wait longer than the gateway allows."""


class ModelAuthError(ModelError):
    """The provider refused the key (401 or 403). Never retried."""


class ModelUnavailable(ModelError):
    """The provider failed (5xx, connection, malformed reply) or the output was invalid."""
