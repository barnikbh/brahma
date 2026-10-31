"""Append-only clinical audit, history and export (contract C2).

The public interface is ``AuditService`` plus the shared models below. There is no
update or delete operation; the database refuses both (BR1.1).
"""

from brahma.platform.audit.models import (
    AuditEntry,
    AuditEntryIn,
    SessionDetail,
    SessionFilter,
    SessionRecord,
    SessionRecordIn,
    SessionSummary,
)
from brahma.platform.audit.service import AuditService

__all__ = [
    "AuditEntry",
    "AuditEntryIn",
    "AuditService",
    "SessionDetail",
    "SessionFilter",
    "SessionRecord",
    "SessionRecordIn",
    "SessionSummary",
]
