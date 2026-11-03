"""Data access for ``ag_walk`` and ``ag_explore_lane`` (FR5.9, FR4.7, NFR8.3).

Every write runs in its own ``BEGIN IMMEDIATE`` transaction, so a saved walk is either
the old or the new state, never half of each.
"""

from __future__ import annotations

import sqlite3

from brahma.agent.models import ExploreLane, TraverseChoice, Walk
from brahma.platform.base import utc_now
from brahma.platform.db import transaction


class WalkRepository:
    """Stores walks and their explore lanes."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # --- walks -----------------------------------------------------------------------

    def create(self, walk: Walk) -> None:
        """Insert a new walk."""
        with transaction(self._conn):
            self._conn.execute(
                "INSERT INTO ag_walk (walk_id, case_id, status, body_json, started_at, "
                "updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    walk.walk_id,
                    walk.case_id,
                    walk.status,
                    walk.model_dump_json(by_alias=True),
                    walk.started_at,
                    utc_now(),
                ),
            )

    def save_progress(self, walk: Walk) -> None:
        """Store the walk's current state (after each section, form or failure)."""
        with transaction(self._conn):
            cursor = self._conn.execute(
                "UPDATE ag_walk SET status = ?, body_json = ?, updated_at = ? WHERE walk_id = ?",
                (walk.status, walk.model_dump_json(by_alias=True), utc_now(), walk.walk_id),
            )
            if cursor.rowcount != 1:
                raise sqlite3.IntegrityError(f"walk not stored: {walk.walk_id}")

    def get(self, walk_id: str) -> Walk | None:
        """The walk, or None."""
        row = self._conn.execute(
            "SELECT body_json FROM ag_walk WHERE walk_id = ?", (walk_id,)
        ).fetchone()
        return Walk.model_validate_json(row["body_json"]) if row is not None else None

    def latest_for_case(self, case_id: str) -> Walk | None:
        """The case's most recently started walk, or None."""
        row = self._conn.execute(
            "SELECT body_json FROM ag_walk WHERE case_id = ? "
            "ORDER BY started_at DESC, rowid DESC LIMIT 1",
            (case_id,),
        ).fetchone()
        return Walk.model_validate_json(row["body_json"]) if row is not None else None

    # --- explore lanes ---------------------------------------------------------------

    def add_lane(self, lane: ExploreLane) -> None:
        """Insert an open lane; one open lane per walk and branch (unique index)."""
        with transaction(self._conn):
            self._conn.execute(
                "INSERT INTO ag_explore_lane (lane_id, walk_id, branch_node_id, status, "
                "body_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    lane.lane_id,
                    lane.walk_id,
                    lane.branch_node_id,
                    lane.status,
                    lane.model_dump_json(by_alias=True),
                    lane.created_at,
                ),
            )

    def save_lane(self, lane: ExploreLane) -> None:
        """Store a lane's lines or its move to ``stopped``."""
        with transaction(self._conn):
            self._conn.execute(
                "UPDATE ag_explore_lane SET status = ?, body_json = ? WHERE lane_id = ?",
                (lane.status, lane.model_dump_json(by_alias=True), lane.lane_id),
            )

    def open_lane(self, walk_id: str, branch_node_id: str) -> ExploreLane | None:
        """The walk's open lane for a branch, or None."""
        row = self._conn.execute(
            "SELECT body_json FROM ag_explore_lane WHERE walk_id = ? AND branch_node_id = ? "
            "AND status = 'open'",
            (walk_id, branch_node_id),
        ).fetchone()
        return ExploreLane.model_validate_json(row["body_json"]) if row is not None else None

    def lanes_for_walk(self, walk_id: str) -> list[ExploreLane]:
        """Every lane of a walk in the order they were opened."""
        rows = self._conn.execute(
            "SELECT body_json FROM ag_explore_lane WHERE walk_id = ? ORDER BY created_at, rowid",
            (walk_id,),
        )
        return [ExploreLane.model_validate_json(r["body_json"]) for r in rows]

    # --- traverse choices ------------------------------------------------------------

    def add_choice(self, choice: TraverseChoice) -> None:
        """Append a choice; rows are never updated, the latest per tier wins."""
        with transaction(self._conn):
            self._conn.execute(
                "INSERT INTO ag_traverse_choice (choice_id, walk_id, tier_id, node_id, "
                "body_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    choice.choice_id,
                    choice.walk_id,
                    choice.tier_id,
                    choice.node_id,
                    choice.model_dump_json(by_alias=True),
                    choice.created_at,
                ),
            )

    def choices_for_walk(self, walk_id: str) -> dict[str, str]:
        """The latest chosen drug per tier, oldest tier first."""
        rows = self._conn.execute(
            "SELECT body_json FROM ag_traverse_choice WHERE walk_id = ? ORDER BY created_at, rowid",
            (walk_id,),
        )
        choices: dict[str, str] = {}
        for row in rows:
            choice = TraverseChoice.model_validate_json(row["body_json"])
            choices[choice.tier_id] = choice.node_id
        return choices
