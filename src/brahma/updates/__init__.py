"""Brahma knowledge updates (U5): doctor proposals, reviewer publishing and source checks.

Decision support, not diagnosis. Nothing a doctor, the drafter or the scheduler proposes
becomes live until a clinical reviewer publishes it, which calls C1 ``create_version``
and writes the C2 audit. Source pages are fetched safely (http(s) only, public addresses
only, 10 MB / 20 s) and treated as data, never instructions. A draft that repeats more
than 25 consecutive source words is flagged and cannot be published.

The public interface is ``UpdateService`` plus the C9 router in ``brahma.updates.api``.
"""

from brahma.updates.errors import (
    CopyFlagged,
    DraftFailed,
    ProposalClosed,
    ProposalInvalid,
    ProposalNotFound,
    SourceFetchError,
    UpdateError,
)
from brahma.updates.models import (
    DraftedChange,
    DraftedChanges,
    FetchedSource,
    LinkedSource,
    Proposal,
    ProposalChange,
    ProposalIn,
    SourceCheckRun,
    VersionHistoryEntry,
)
from brahma.updates.service import UpdateService

__all__ = [
    "CopyFlagged",
    "DraftFailed",
    "DraftedChange",
    "DraftedChanges",
    "FetchedSource",
    "LinkedSource",
    "Proposal",
    "ProposalChange",
    "ProposalClosed",
    "ProposalIn",
    "ProposalInvalid",
    "ProposalNotFound",
    "SourceCheckRun",
    "SourceFetchError",
    "UpdateError",
    "UpdateService",
    "VersionHistoryEntry",
]
