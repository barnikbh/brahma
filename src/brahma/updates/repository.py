"""Parameterised SQL for the ``up_`` tables (US8.1, US8.2).

Write methods run inside the caller's transaction (``brahma.platform.db.transaction``),
so a status change and its audit entry commit together. There is no delete path.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from brahma.knowledge.models import ChangeSet
from brahma.platform.base import new_id, to_json, utc_now
from brahma.updates.errors import ProposalClosed, ProposalNotFound
from brahma.updates.models import (
    LinkedSource,
    Proposal,
    ProposalChange,
    ProposalStatus,
    SourceCheckRun,
    SourceStatus,
    Thread,
    ThreadMessage,
    ThreadStatus,
)


def _json_or_none(value: str | None) -> Any:
    return json.loads(value) if value is not None else None


def _change_from_row(row: sqlite3.Row) -> ProposalChange:
    return ProposalChange(
        node_id=row["node_id"],
        before=_json_or_none(row["before_json"]),
        after=json.loads(row["after_json"]),
        source_passage=row["source_passage"],
        source_url=row["source_url"],
        copy_flag=bool(row["copy_flag"]),
    )


def _source_from_row(row: sqlite3.Row) -> LinkedSource:
    return LinkedSource(
        source_id=row["source_id"],
        pack=row["pack"],
        url=row["url"],
        title=row["title"],
        content_hash=row["content_hash"],
        last_checked_at=row["last_checked_at"],
        last_status=row["last_status"],
    )


class UpdateRepository:
    """Inserts, reads and status changes for proposals, linked sources and check runs."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # --- proposals -------------------------------------------------------------------

    def insert_proposal(self, proposal: Proposal) -> None:
        """Insert a proposal and its per-node changes (inside the caller's transaction)."""
        self._conn.execute(
            "INSERT INTO up_proposal (proposal_id, pack, base_version, target_version, "
            "proposer_profile_id, origin, change_set_json, comment, status, source_id, "
            "reviewer_profile_id, review_comment, published_version, created_at, decided_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                proposal.proposal_id,
                proposal.pack,
                proposal.base_version,
                proposal.target_version,
                proposal.proposer_profile_id,
                proposal.origin,
                proposal.change_set.model_dump_json(by_alias=True),
                proposal.comment,
                proposal.status,
                proposal.source_id,
                proposal.reviewer_profile_id,
                proposal.review_comment,
                proposal.published_version,
                proposal.created_at,
                proposal.decided_at,
            ),
        )
        for position, change in enumerate(proposal.changes):
            self._conn.execute(
                "INSERT INTO up_proposal_change (proposal_id, position, node_id, before_json, "
                "after_json, source_passage, source_url, copy_flag) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    proposal.proposal_id,
                    position,
                    change.node_id,
                    to_json(change.before) if change.before is not None else None,
                    to_json(change.after),
                    change.source_passage,
                    change.source_url,
                    int(change.copy_flag),
                ),
            )

    def get_proposal(self, proposal_id: str) -> Proposal | None:
        """The proposal with its changes in order, or None."""
        row = self._conn.execute(
            "SELECT * FROM up_proposal WHERE proposal_id = ?", (proposal_id,)
        ).fetchone()
        return self._proposal(row) if row is not None else None

    def list_proposals(
        self, pack: str | None = None, status: ProposalStatus | None = None
    ) -> list[Proposal]:
        """Proposals newest first, optionally only one pack and one status."""
        clauses: list[str] = []
        params: list[str] = []
        if pack is not None:
            clauses.append("pack = ?")
            params.append(pack)
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._conn.execute(
            f"SELECT * FROM up_proposal{where} ORDER BY created_at DESC, rowid DESC", params
        ).fetchall()
        return [self._proposal(row) for row in rows]

    def set_status(
        self,
        proposal_id: str,
        status: ProposalStatus,
        reviewer_profile_id: str,
        review_comment: str | None,
        published_version: str | None = None,
    ) -> None:
        """Move a ``proposed`` proposal to ``published`` or ``rejected``.

        Raises ProposalNotFound for an unknown ID and ProposalClosed when it is no longer
        ``proposed`` (both end states are terminal).
        """
        if status == "proposed":
            raise ValueError("a proposal can only move to published or rejected")
        cursor = self._conn.execute(
            "UPDATE up_proposal SET status = ?, reviewer_profile_id = ?, review_comment = ?, "
            "published_version = ?, decided_at = ? WHERE proposal_id = ? AND status = 'proposed'",
            (
                status,
                reviewer_profile_id,
                review_comment,
                published_version,
                utc_now(),
                proposal_id,
            ),
        )
        if cursor.rowcount == 1:
            return
        current = self._conn.execute(
            "SELECT status FROM up_proposal WHERE proposal_id = ?", (proposal_id,)
        ).fetchone()
        if current is None:
            raise ProposalNotFound(proposal_id)
        raise ProposalClosed(proposal_id, current["status"])

    def _proposal(self, row: sqlite3.Row) -> Proposal:
        changes = self._conn.execute(
            "SELECT * FROM up_proposal_change WHERE proposal_id = ? ORDER BY position",
            (row["proposal_id"],),
        ).fetchall()
        return Proposal(
            proposal_id=row["proposal_id"],
            pack=row["pack"],
            base_version=row["base_version"],
            target_version=row["target_version"],
            proposer_profile_id=row["proposer_profile_id"],
            origin=row["origin"],
            change_set=ChangeSet.model_validate_json(row["change_set_json"]),
            comment=row["comment"],
            status=row["status"],
            source_id=row["source_id"],
            reviewer_profile_id=row["reviewer_profile_id"],
            review_comment=row["review_comment"],
            published_version=row["published_version"],
            created_at=row["created_at"],
            decided_at=row["decided_at"],
            changes=[_change_from_row(c) for c in changes],
        )

    # --- node provenance -------------------------------------------------------------

    def published_node_changes(self, pack: str) -> list[sqlite3.Row]:
        """Every node change of a published proposal of this pack, oldest first."""
        return self._conn.execute(
            "SELECT c.node_id, p.proposal_id, p.published_version, p.proposer_profile_id, "
            "p.reviewer_profile_id, p.decided_at FROM up_proposal_change c "
            "JOIN up_proposal p ON p.proposal_id = c.proposal_id "
            "WHERE p.pack = ? AND p.status = 'published' ORDER BY p.decided_at, p.rowid",
            (pack,),
        ).fetchall()

    # --- update conversations --------------------------------------------------------

    def insert_thread(self, thread: Thread) -> None:
        """Insert an empty conversation (inside the caller's transaction)."""
        self._conn.execute(
            "INSERT INTO up_thread (thread_id, pack, profile_id, status, rounds, created_at, "
            "updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                thread.thread_id,
                thread.pack,
                thread.profile_id,
                thread.status,
                thread.rounds,
                thread.created_at,
                thread.updated_at,
            ),
        )

    def append_message(
        self, thread_id: str, role: str, text: str, proposal_id: str | None = None
    ) -> None:
        """Add a message at the next position."""
        self._conn.execute(
            "INSERT INTO up_thread_message (thread_id, position, role, text, proposal_id, "
            "created_at) VALUES (?, (SELECT COUNT(*) FROM up_thread_message WHERE thread_id = ?), "
            "?, ?, ?, ?)",
            (thread_id, thread_id, role, text, proposal_id, utc_now()),
        )

    def update_thread(self, thread_id: str, status: ThreadStatus, rounds: int) -> None:
        """Set a conversation's status and round count and touch its time."""
        self._conn.execute(
            "UPDATE up_thread SET status = ?, rounds = ?, updated_at = ? WHERE thread_id = ?",
            (status, rounds, utc_now(), thread_id),
        )

    def get_thread(self, thread_id: str) -> Thread | None:
        """A conversation with its messages in order, or None."""
        row = self._conn.execute(
            "SELECT * FROM up_thread WHERE thread_id = ?", (thread_id,)
        ).fetchone()
        return self._thread(row) if row is not None else None

    def list_threads(self, profile_id: str) -> list[Thread]:
        """One doctor's conversations, most recently updated first."""
        rows = self._conn.execute(
            "SELECT * FROM up_thread WHERE profile_id = ? ORDER BY updated_at DESC, rowid DESC",
            (profile_id,),
        ).fetchall()
        return [self._thread(r) for r in rows]

    def _thread(self, row: sqlite3.Row) -> Thread:
        messages = self._conn.execute(
            "SELECT * FROM up_thread_message WHERE thread_id = ? ORDER BY position",
            (row["thread_id"],),
        ).fetchall()
        return Thread(
            thread_id=row["thread_id"],
            pack=row["pack"],
            profile_id=row["profile_id"],
            status=row["status"],
            rounds=row["rounds"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            messages=[
                ThreadMessage(
                    position=m["position"],
                    role=m["role"],
                    text=m["text"],
                    proposal_id=m["proposal_id"],
                    created_at=m["created_at"],
                )
                for m in messages
            ],
        )

    # --- linked sources --------------------------------------------------------------

    def upsert_linked_source(
        self, pack: str, url: str, title: str, content_hash: str | None
    ) -> LinkedSource:
        """Insert the source for (pack, url), or refresh its title and hash; return it."""
        now = utc_now()
        self._conn.execute(
            "INSERT INTO up_linked_source (source_id, pack, url, title, content_hash, "
            "last_checked_at, last_status) VALUES (?, ?, ?, ?, ?, ?, 'ok') "
            "ON CONFLICT (pack, url) DO UPDATE SET title = excluded.title, "
            "content_hash = excluded.content_hash, last_checked_at = excluded.last_checked_at, "
            "last_status = 'ok'",
            (new_id("ls"), pack, url, title, content_hash, now),
        )
        row = self._conn.execute(
            "SELECT * FROM up_linked_source WHERE pack = ? AND url = ?", (pack, url)
        ).fetchone()
        return _source_from_row(row)

    def update_source_check(
        self, source_id: str, status: SourceStatus, content_hash: str | None = None
    ) -> None:
        """Record a check of one source: its status, and its new hash when one is given."""
        self._conn.execute(
            "UPDATE up_linked_source SET last_status = ?, last_checked_at = ?, "
            "content_hash = COALESCE(?, content_hash) WHERE source_id = ?",
            (status, utc_now(), content_hash, source_id),
        )

    def list_linked_sources(self) -> list[LinkedSource]:
        """Every linked source, oldest first."""
        rows = self._conn.execute("SELECT * FROM up_linked_source ORDER BY rowid").fetchall()
        return [_source_from_row(row) for row in rows]

    def get_linked_source(self, source_id: str) -> LinkedSource | None:
        """One linked source, or None."""
        row = self._conn.execute(
            "SELECT * FROM up_linked_source WHERE source_id = ?", (source_id,)
        ).fetchone()
        return _source_from_row(row) if row is not None else None

    # --- scheduler runs --------------------------------------------------------------

    def insert_check_run(self, run: SourceCheckRun) -> None:
        """Insert one scheduler run record."""
        self._conn.execute(
            "INSERT INTO up_source_check_run (run_id, started_at, finished_at, checked, "
            "changed, failed, errors_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                run.run_id,
                run.started_at,
                run.finished_at,
                run.checked,
                run.changed,
                run.failed,
                to_json(run.errors),
            ),
        )

    def list_check_runs(self) -> list[SourceCheckRun]:
        """Scheduler runs, newest first."""
        rows = self._conn.execute(
            "SELECT * FROM up_source_check_run ORDER BY started_at DESC, rowid DESC"
        ).fetchall()
        return [
            SourceCheckRun(
                run_id=r["run_id"],
                started_at=r["started_at"],
                finished_at=r["finished_at"],
                checked=r["checked"],
                changed=r["changed"],
                failed=r["failed"],
                errors=json.loads(r["errors_json"]),
            )
            for r in rows
        ]
