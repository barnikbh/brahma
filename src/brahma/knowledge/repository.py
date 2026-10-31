"""Data access for the ``kg_`` tables (logical-components.md KnowledgeRepository).

There is no update or delete path for published rows; the only change is
``supersede``. Writes run inside ``transaction()``, which begins with
``BEGIN IMMEDIATE`` so the write lock is taken before anything is read.
"""

from __future__ import annotations

import re
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from datetime import UTC, datetime

from brahma.knowledge.db import LockedConnection
from brahma.knowledge.errors import (
    BaseNotLive,
    CommentInvalid,
    NodeNotFound,
    PackBusy,
    PackLoadError,
    VersionNotIncreasing,
)
from brahma.knowledge.models import (
    Edge,
    Node,
    NodeComment,
    Pack,
    PackHeader,
    PackVersion,
    Source,
    parse_version,
)

_VERSION_COLUMNS = (
    "pack_version_id, pack_id, number, status, published_at, published_by, change_summary, based_on"
)


COMMENT_MAX_CHARS = 1000
_CONTROL_CHARS = re.compile(r"[\x00-\x09\x0b-\x1f\x7f]")


def clean_comment_text(text: str) -> str:
    """Strip control characters except newline, then require 1-1,000 non-blank characters.

    The text is otherwise kept as given: U1 never renders it, and screens escape it.
    """
    cleaned = _CONTROL_CHARS.sub("", text)
    if not cleaned.strip():
        raise CommentInvalid("comment text is blank")
    if len(cleaned) > COMMENT_MAX_CHARS:
        raise CommentInvalid(f"comment text is {len(cleaned)} characters; the limit is 1000")
    return cleaned


def utc_now() -> str:
    """Current UTC time as an ISO 8601 string with microseconds."""
    return datetime.now(UTC).isoformat(timespec="microseconds")


def version_id(pack: str, number: str) -> str:
    """The stored identifier of a pack version, e.g. ``IBD@1.0``."""
    return f"{pack}@{number}"


def _version(row: sqlite3.Row) -> PackVersion:
    return PackVersion(
        pack_version_id=row["pack_version_id"],
        pack=row["pack_id"],
        number=row["number"],
        status=row["status"],
        published_at=row["published_at"],
        published_by=row["published_by"],
        change_summary=row["change_summary"],
        based_on=row["based_on"],
    )


class KnowledgeRepository:
    """All SQL for U1. Methods other than reads must run inside ``transaction()``."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Run the block in one ``BEGIN IMMEDIATE`` transaction; roll back on any error.

        The connection's lock is held for the whole block, so two threads can never
        interleave their transactions.
        """
        hold = self.conn.locked() if isinstance(self.conn, LockedConnection) else nullcontext(None)
        with hold:
            try:
                self.conn.execute("BEGIN IMMEDIATE")
            except sqlite3.OperationalError as exc:
                if "locked" in str(exc) or "busy" in str(exc):
                    raise PackBusy("the knowledge database is busy; try again") from exc
                raise
            try:
                yield
            except BaseException:
                self.conn.execute("ROLLBACK")
                raise
            self.conn.execute("COMMIT")

    # --- packs and versions --------------------------------------------------------

    def get_pack(self, code: str) -> Pack | None:
        row = self.conn.execute("SELECT * FROM kg_pack WHERE pack_id = ?", (code,)).fetchone()
        if row is None:
            return None
        live = self.live_version(code)
        return Pack(
            pack_id=row["pack_id"],
            name=row["name"],
            code=row["code"],
            specialty=row["specialty"],
            live_version_number=live.number if live else None,
        )

    def insert_pack(self, header: PackHeader) -> None:
        try:
            self.conn.execute(
                "INSERT INTO kg_pack (pack_id, code, name, specialty) VALUES (?, ?, ?, ?)",
                (header.code, header.code, header.name, header.specialty),
            )
        except sqlite3.IntegrityError as exc:
            raise PackLoadError(header.code, f"pack name or code already used: {exc}") from exc

    def live_version(self, code: str) -> PackVersion | None:
        row = self.conn.execute(
            f"SELECT {_VERSION_COLUMNS} FROM kg_pack_version WHERE pack_id = ? AND status = 'live'",
            (code,),
        ).fetchone()
        return _version(row) if row else None

    def live_versions(self) -> list[PackVersion]:
        rows = self.conn.execute(
            f"SELECT {_VERSION_COLUMNS} FROM kg_pack_version WHERE status = 'live' ORDER BY pack_id"
        ).fetchall()
        return [_version(row) for row in rows]

    def get_version(self, code: str, number: str) -> PackVersion | None:
        row = self.conn.execute(
            f"SELECT {_VERSION_COLUMNS} FROM kg_pack_version WHERE pack_version_id = ?",
            (version_id(code, number),),
        ).fetchone()
        return _version(row) if row else None

    def list_versions(self, code: str) -> list[PackVersion]:
        rows = self.conn.execute(
            f"SELECT {_VERSION_COLUMNS} FROM kg_pack_version WHERE pack_id = ? "
            "ORDER BY major DESC, minor DESC",
            (code,),
        ).fetchall()
        return [_version(row) for row in rows]

    def insert_version(
        self, code: str, number: str, published_by: str, change_summary: str, based_on: str | None
    ) -> PackVersion:
        major, minor = parse_version(number)
        pv_id = version_id(code, number)
        self.conn.execute(
            "INSERT INTO kg_pack_version (pack_version_id, pack_id, number, major, minor, status, "
            "published_at, published_by, change_summary, based_on) "
            "VALUES (?, ?, ?, ?, ?, 'live', ?, ?, ?, ?)",
            (pv_id, code, number, major, minor, utc_now(), published_by, change_summary, based_on),
        )
        stored = self.get_version(code, number)
        assert stored is not None  # just inserted in this transaction
        return stored

    def supersede(self, pack_version_id: str) -> None:
        """Mark a live version superseded: the only change ever made to a stored version."""
        self.conn.execute(
            "UPDATE kg_pack_version SET status = 'superseded' "
            "WHERE pack_version_id = ? AND status = 'live'",
            (pack_version_id,),
        )

    # --- sources, nodes, edges -----------------------------------------------------

    def insert_sources(self, code: str, sources: list[Source]) -> None:
        """Store new sources; an existing ID must be identical and belong to the same pack."""
        for source in sources:
            body = source.model_dump_json()
            row = self.conn.execute(
                "SELECT pack_id, body_json FROM kg_source WHERE source_id = ?",
                (source.source_id,),
            ).fetchone()
            if row is None:
                self.conn.execute(
                    "INSERT INTO kg_source (source_id, pack_id, body_json) VALUES (?, ?, ?)",
                    (source.source_id, code, body),
                )
            elif row["pack_id"] != code or Source.model_validate_json(row["body_json"]) != source:
                raise PackLoadError(
                    source.source_id,
                    "a stored source with this ID differs; sources are immutable, use a new ID",
                )

    def read_sources(self, code: str) -> list[Source]:
        rows = self.conn.execute(
            "SELECT body_json FROM kg_source WHERE pack_id = ? ORDER BY source_id", (code,)
        ).fetchall()
        return [Source.model_validate_json(row["body_json"]) for row in rows]

    def insert_nodes(self, pack_version_id: str, nodes: list[Node]) -> None:
        self.conn.executemany(
            "INSERT INTO kg_node (pack_version_id, node_id, type, body_json) VALUES (?, ?, ?, ?)",
            [
                (
                    pack_version_id,
                    node.node_id,
                    node.type,
                    node.model_dump_json(exclude={"pack_version"}),
                )
                for node in nodes
            ],
        )

    def insert_edges(self, pack_version_id: str, edges: list[Edge]) -> None:
        self.conn.executemany(
            "INSERT INTO kg_edge (pack_version_id, edge_id, from_node_id, to_node_id, body_json) "
            "VALUES (?, ?, ?, ?, ?)",
            [
                (pack_version_id, e.edge_id, e.from_node_id, e.to_node_id, e.model_dump_json())
                for e in edges
            ],
        )

    def read_nodes(self, pack_version_id: str) -> list[Node]:
        rows = self.conn.execute(
            "SELECT body_json FROM kg_node WHERE pack_version_id = ? ORDER BY node_id",
            (pack_version_id,),
        ).fetchall()
        return [Node.model_validate_json(row["body_json"]) for row in rows]

    def read_edges(self, pack_version_id: str) -> list[Edge]:
        rows = self.conn.execute(
            "SELECT body_json FROM kg_edge WHERE pack_version_id = ? ORDER BY edge_id",
            (pack_version_id,),
        ).fetchall()
        return [Edge.model_validate_json(row["body_json"]) for row in rows]

    def node_exists(self, node_id: str) -> bool:
        """True when any version of any pack holds this node ID."""
        row = self.conn.execute("SELECT 1 FROM kg_node WHERE node_id = ? LIMIT 1", (node_id,))
        return row.fetchone() is not None

    # --- comments ------------------------------------------------------------------

    def add_comment(self, node_id: str, author_profile_id: str, text: str) -> str:
        """Validate and store a comment in one transaction (BR2.7, NFR6.2)."""
        cleaned = clean_comment_text(text)
        with self.transaction():
            if not self.node_exists(node_id):
                raise NodeNotFound(node_id)
            return self.insert_comment(node_id, author_profile_id, cleaned)

    def insert_comment(self, node_id: str, author_profile_id: str, text: str) -> str:
        comment_id = uuid.uuid4().hex
        self.conn.execute(
            "INSERT INTO kg_comment (comment_id, node_id, author_profile_id, text, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (comment_id, node_id, author_profile_id, text, utc_now()),
        )
        return comment_id

    def list_comments(self, node_id: str) -> list[NodeComment]:
        rows = self.conn.execute(
            "SELECT * FROM kg_comment WHERE node_id = ? ORDER BY created_at DESC, rowid DESC",
            (node_id,),
        ).fetchall()
        return [
            NodeComment(
                comment_id=row["comment_id"],
                node_id=row["node_id"],
                author_profile_id=row["author_profile_id"],
                text=row["text"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    # --- one atomic publish ----------------------------------------------------------

    def publish(
        self,
        header: PackHeader,
        content: VersionContent,
        published_by: str,
        *,
        number: str | None = None,
        base_number: str | None = None,
    ) -> PackVersion:
        """Store a new live version and supersede the old one, in one transaction (BR1.3).

        Pass ``number`` for a pack-file load: it must be higher than the live number.
        Pass ``base_number`` for ``create_version``: it must still be the live number, and
        the new version gets the next minor number. The checks run after the write lock is
        taken, so two overlapping publishes can never leave two live versions.
        """
        with self.transaction():
            live = self.live_version(header.code)
            new_number = self._next_number(header.code, live, number, base_number)
            if self.get_pack(header.code) is None:
                self.insert_pack(header)
            self.insert_sources(header.code, content.sources)
            if live is not None:
                self.supersede(live.pack_version_id)
            summary = content.change_summary or ("Initial load" if live is None else "Reload")
            based_on = live.pack_version_id if live is not None else None
            stored = self.insert_version(header.code, new_number, published_by, summary, based_on)
            self.insert_nodes(stored.pack_version_id, content.nodes)
            self.insert_edges(stored.pack_version_id, content.edges)
        return stored

    @staticmethod
    def _next_number(
        code: str, live: PackVersion | None, number: str | None, base_number: str | None
    ) -> str:
        if base_number is not None:
            if live is None or live.number != base_number:
                raise BaseNotLive(code, base_number, live.number if live else None)
            major, minor = parse_version(live.number)
            return f"{major}.{minor + 1}"
        if number is None:
            raise ValueError("publish needs a number or a base_number")
        if live is not None and parse_version(number) <= parse_version(live.number):
            raise VersionNotIncreasing(code, number, live.number)
        return number


class VersionContent:
    """The sources, nodes and edges of one version, ready to store."""

    def __init__(
        self,
        sources: list[Source],
        nodes: list[Node],
        edges: list[Edge],
        change_summary: str | None = None,
    ) -> None:
        self.sources = sources
        self.nodes = nodes
        self.edges = edges
        self.change_summary = change_summary
