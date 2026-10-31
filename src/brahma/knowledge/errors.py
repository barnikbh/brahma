"""Typed errors raised by the knowledge graph (functional-spec.md, security-design.md)."""

from __future__ import annotations


class KnowledgeError(Exception):
    """Base class for every error the knowledge graph raises."""


class PackLoadError(KnowledgeError):
    """A pack file or a ChangeSet failed validation; nothing was stored.

    ``item_id`` names the first offending node, edge, source or file.
    """

    def __init__(self, item_id: str, reason: str) -> None:
        super().__init__(f"{item_id}: {reason}")
        self.item_id = item_id
        self.reason = reason


class PackBusy(KnowledgeError):
    """The database write lock was not obtained within the busy timeout."""


class VersionNotIncreasing(KnowledgeError):
    """A load named a version number that is not higher than the live one."""

    def __init__(self, pack: str, number: str, live: str) -> None:
        super().__init__(f"{pack}: version {number} is not higher than live version {live}")
        self.pack = pack
        self.number = number
        self.live = live


class BaseNotLive(KnowledgeError):
    """create_version was given a base version that is not the pack's live version."""

    def __init__(self, pack: str, base: str, live: str | None) -> None:
        super().__init__(f"{pack}: base version {base} is not live (live is {live})")
        self.pack = pack
        self.base = base
        self.live = live


class VersionRequired(KnowledgeError):
    """A read did not name a pack version (BR1.5)."""


class VersionNotFound(KnowledgeError):
    """A read named a pack or version that does not exist."""

    def __init__(self, pack: str, number: str | None = None) -> None:
        label = pack if number is None else f"{pack}@{number}"
        super().__init__(f"unknown pack version: {label}")
        self.pack = pack
        self.number = number


class NodeNotFound(KnowledgeError):
    """The node ID does not exist in the version read (or in any version, for comments)."""

    def __init__(self, node_id: str) -> None:
        super().__init__(f"unknown node: {node_id}")
        self.node_id = node_id


class CommentInvalid(KnowledgeError):
    """A comment's text is blank or longer than 1,000 characters after cleaning."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason
