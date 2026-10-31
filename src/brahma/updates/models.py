"""Pydantic models for knowledge updates (entities.md, contract C9).

Python attributes are snake_case; the wire names are camelCase aliases (``proposalId``).
Every model refuses unknown keys and is immutable once built.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from brahma.knowledge.models import PACK_CODE_PATTERN, ChangeSet

ProposalStatus = Literal["proposed", "published", "rejected"]
ProposalOrigin = Literal["doctor", "drafted", "scheduled"]
SourceStatus = Literal["new", "ok", "changed", "failed"]
HistoryStatus = Literal["live", "superseded", "proposed", "rejected"]
PROPOSAL_STATUSES: tuple[str, ...] = ("proposed", "published", "rejected")
PROPOSAL_ORIGINS: tuple[str, ...] = ("doctor", "drafted", "scheduled")
SOURCE_STATUSES: tuple[str, ...] = ("new", "ok", "changed", "failed")

MAX_COMMENT_LENGTH = 2000
MAX_URL_LENGTH = 2048


class UpModel(BaseModel):
    """Base model: camelCase aliases, snake_case attributes, unknown keys refused, immutable."""

    model_config = ConfigDict(
        extra="forbid",
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
        serialize_by_alias=True,
        frozen=True,
    )


def _not_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("must not be blank")
    return value.strip()


# --- Stored entities -------------------------------------------------------------------


class ProposalChange(UpModel):
    """One changed node: its value before and after, the source passage and the copy flag."""

    node_id: str = Field(min_length=1)
    before: dict[str, Any] | None = None
    after: dict[str, Any]
    source_passage: str | None = None
    source_url: str | None = None
    copy_flag: bool = False


class Proposal(UpModel):
    """A suggested change to a pack. Never live until a reviewer publishes it (BR1.1)."""

    proposal_id: str
    pack: str = Field(pattern=PACK_CODE_PATTERN)
    base_version: str
    target_version: str
    proposer_profile_id: str
    origin: ProposalOrigin
    change_set: ChangeSet
    comment: str
    status: ProposalStatus
    source_id: str | None = None
    reviewer_profile_id: str | None = None
    review_comment: str | None = None
    published_version: str | None = None
    created_at: str
    decided_at: str | None = None
    changes: list[ProposalChange] = Field(default_factory=list)

    @property
    def copy_flagged_node_ids(self) -> list[str]:
        """The node IDs whose drafted text may copy the source verbatim (BR2.3)."""
        return [c.node_id for c in self.changes if c.copy_flag]


class LinkedSource(UpModel):
    """A source page a proposal linked; the scheduler re-checks it (BR4.1)."""

    source_id: str
    pack: str = Field(pattern=PACK_CODE_PATTERN)
    url: str
    title: str
    content_hash: str | None = None
    last_checked_at: str | None = None
    last_status: SourceStatus = "new"


class SourceCheckRun(UpModel):
    """One scheduler run: how many sources were checked, changed and failed."""

    run_id: str
    started_at: str
    finished_at: str
    checked: int = Field(ge=0)
    changed: int = Field(ge=0)
    failed: int = Field(ge=0)
    errors: list[dict[str, str]] = Field(default_factory=list)


# --- Values and call shapes (not stored) -----------------------------------------------


class FetchedSource(UpModel):
    """A fetched page reduced to plain text. The text is data, never instructions."""

    url: str
    title: str
    text: str
    content_hash: str
    bytes: int = Field(ge=0)


class ProposalIn(UpModel):
    """A doctor's proposal (BR1.1): one node, a change to its fields and a comment.

    ``change`` holds the node keys to replace, by their camelCase names (``content``,
    ``label``, ``fields``, ``sourceIds`` ...). ``nodeId`` and ``type`` cannot change.
    """

    pack: str = Field(default="IBD", pattern=PACK_CODE_PATTERN)
    node_id: str = Field(min_length=1)
    change: dict[str, Any] = Field(min_length=1)
    comment: str = Field(min_length=1, max_length=MAX_COMMENT_LENGTH)
    source_url: str | None = Field(default=None, max_length=MAX_URL_LENGTH)
    section: str | None = Field(default=None, max_length=20_000)

    _check_comment = field_validator("comment")(_not_blank)


class DraftedChange(UpModel):
    """One node update drafted by the model: new paraphrased content for an existing node."""

    node_id: str = Field(min_length=1)
    content: str = Field(min_length=1, max_length=4000)
    label: str | None = Field(default=None, max_length=80)


class DraftedChanges(UpModel):
    """The structured output of the ``draft_proposal`` call (BR3.1). Unknown keys refused."""

    changes: list[DraftedChange]
    summary: str = Field(min_length=1, max_length=MAX_COMMENT_LENGTH)


class VersionHistoryEntry(UpModel):
    """One history row: a C1 version (live, superseded) or a proposal (proposed, rejected)."""

    version: str
    status: HistoryStatus
    date: str
    author: str
    author_name: str | None = None
    change: str
    comment: str | None = None
    proposal_id: str | None = None


ThreadStatus = Literal["open", "proposed", "stuck"]
MAX_MESSAGE_LENGTH = 4000


class ThreadMessage(UpModel):
    """One message in an update conversation: the doctor's or the assistant's."""

    position: int = Field(ge=0)
    role: Literal["doctor", "assistant"]
    text: str
    proposal_id: str | None = None
    created_at: str


class Thread(UpModel):
    """An update conversation: messages, the open-question round count and its status."""

    thread_id: str
    pack: str = Field(pattern=PACK_CODE_PATTERN)
    profile_id: str
    status: ThreadStatus
    rounds: int = Field(ge=0)
    created_at: str
    updated_at: str
    messages: list[ThreadMessage] = Field(default_factory=list)


class NodeProvenance(UpModel):
    """Who last updated a node, when, and in which published version (BR1)."""

    node_id: str
    updated_by: str
    updated_by_name: str
    approved_by: str
    approved_by_name: str
    updated_at: str
    version: str
    proposal_id: str
